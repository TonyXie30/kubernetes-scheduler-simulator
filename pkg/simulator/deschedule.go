package simulator

import (
	"container/heap"
	"math"
	"sort"

	log "github.com/sirupsen/logrus"
	corev1 "k8s.io/api/core/v1"

	simontype "github.com/hkust-adsl/kubernetes-scheduler-simulator/pkg/type"
	"github.com/hkust-adsl/kubernetes-scheduler-simulator/pkg/utils"
)

const (
	DeschedulePolicyCosSim       = "cosSim"
	DeschedulePolicyFragOnePod   = "fragOnePod"
	DeschedulePolicyFragMultiPod = "fragMultiPod"
	DeschedulePolicyBinPacking   = "binPacking"
)

func (sim *Simulator) DescheduleCluster() []simontype.UnscheduledPod {
	podMap := sim.getCurrentPodMap()

	nodeStatus := sim.GetClusterNodeStatus() // Note: the resources in nodeStatus.Node is the capacity instead of requests
	podDistribution := sim.GetPodDistribution()
	nodeResMap := utils.GetNodeResourceMap(nodeStatus)

	var failedPods []simontype.UnscheduledPod
	numPodsToDeschedule := int(math.Ceil(sim.customConfig.DescheduleConfig.Ratio * float64(len(podMap))))
	log.Infof("maximum number of pods that can be descheduled: %d, deschedule policy: %s\n",
		numPodsToDeschedule, sim.customConfig.DescheduleConfig.Policy)

	switch sim.customConfig.DescheduleConfig.Policy {
	case DeschedulePolicyCosSim:
		failedPods = sim.descheduleClusterOnCosSim(numPodsToDeschedule, nodeStatus, nodeResMap, podMap)

	case DeschedulePolicyFragOnePod:
		failedPods = sim.descheduleClusterOnFragOnePod(numPodsToDeschedule, nodeStatus, nodeResMap, podMap)

	case DeschedulePolicyFragMultiPod:
		failedPods = sim.descheduleClusterOnFragMultiPod(numPodsToDeschedule, nodeStatus, nodeResMap, podMap)

	case DeschedulePolicyBinPacking:
		failedPods = sim.descheduleClusterOnBinPacking(numPodsToDeschedule, nodeStatus, nodeResMap, podMap, podDistribution)

	default:
		log.Errorf("DeschedulePolicy not found\n")
	}

	log.Infof("[DescheduleCluster] Num of Failed Pods: %d\n", len(failedPods))
	return failedPods
}

func (sim *Simulator) descheduleClusterOnCosSim(numPodsToDeschedule int, nodeStatus []simontype.NodeStatus,
	nodeResMap map[string]simontype.NodeResource, podMap map[string]*corev1.Pod) []simontype.UnscheduledPod {

	milliCpuBar := int64(2000) // temporarily hard-code
	milliGpuBar := int64(500)
	sortNodeStatusByResource(milliCpuBar, nodeStatus, nodeResMap)

	var descheduledPodKeys []string
	for _, ns := range nodeStatus {
		if numPodsToDeschedule <= 0 {
			break
		}
		// nodeFilter
		nodeRes := nodeResMap[ns.Node.Name]
		if nodeRes.MilliCpuLeft >= milliCpuBar {
			continue
		}
		gpuBarPass := false
		for _, v := range nodeRes.MilliGpuLeftList {
			if v > milliGpuBar {
				gpuBarPass = true
				break
			}
		}
		if !gpuBarPass {
			continue
		}

		victimPod := sim.findVictimPodOnCosSim(nodeRes, ns.Pods)
		if victimPod != nil {
			if err := sim.deletePod(victimPod); err != nil {
				log.Errorf("[descheduleClusterOnCosSim] failed to delete pod(%s)\n",
					utils.GeneratePodKey(victimPod))
			} else {
				descheduledPodKeys = append(descheduledPodKeys, utils.GeneratePodKey(victimPod))
				numPodsToDeschedule -= 1
			}
		}
	}
	sim.ClusterAnalysis(TagPostEviction)
	descheduledPod := getPodfromPodMap(descheduledPodKeys, podMap)
	log.Infof("[DescheduleCluster] Num of Descheduled Pods: %d\n", len(descheduledPod))
	return sim.SchedulePods(descheduledPod)
}

func (sim *Simulator) descheduleClusterOnFragOnePod(numPodsToDeschedule int, nodeStatus []simontype.NodeStatus,
	nodeResMap map[string]simontype.NodeResource, podMap map[string]*corev1.Pod) []simontype.UnscheduledPod {
	nodeStatusMap := make(map[string]simontype.NodeStatus)
	for _, ns := range nodeStatus {
		nodeStatusMap[ns.Node.Name] = ns
	}

	var descheduledPodKeys []string
	nodeFragAmountList := sim.getNodeFragAmountList(nodeStatus)
	for _, nfa := range nodeFragAmountList { // from nodes with the largest amount of fragment
		if numPodsToDeschedule <= 0 {
			break
		}
		nsPods := nodeStatusMap[nfa.NodeName].Pods
		victimPod, _ := sim.findVictimPodOnNodeFragAware(nfa, nodeResMap[nfa.NodeName], nsPods) // evict one pod per node
		if victimPod != nil {
			descheduledPodKeys = append(descheduledPodKeys, utils.GeneratePodKey(victimPod))
			sim.deletePod(victimPod)
			numPodsToDeschedule -= 1
		}
	}
	sim.ClusterAnalysis(TagPostEviction)
	descheduledPod := getPodfromPodMap(descheduledPodKeys, podMap)
	log.Infof("[DescheduleCluster] Num of Descheduled Pods: %d\n", len(descheduledPod))
	return sim.SchedulePods(descheduledPod)
}

func (sim *Simulator) descheduleClusterOnFragMultiPod(numPodsToDeschedule int, nodeStatus []simontype.NodeStatus,
	nodeResMap map[string]simontype.NodeResource, podMap map[string]*corev1.Pod) []simontype.UnscheduledPod {
	var descheduledPodKeys []string
	nodeFragAmountMap := sim.NodeGpuFragAmountMap(nodeResMap)

	i := 0
	nodeFragQueue := make(PriorityQueue, len(nodeFragAmountMap))
	for _, v := range nodeFragAmountMap {
		nodeFragQueue[i] = &Item{
			value:    v,
			priority: v.FragAmountSumExceptQ3(),
			index:    i,
		}
		i++
	}
	heap.Init(&nodeFragQueue)

	tempNodeStatusMap := make(map[string]simontype.NodeStatus)
	for _, ns := range nodeStatus {
		tempNodeStatusMap[ns.Node.Name] = ns // should not touch ns.Node since it is a pointer
	}

	nodeDescheduleCount := make(map[string]int)
	popCount := 0
	for numPodsToDeschedule > 0 {
		if nodeFragQueue.Len() == 0 {
			break
		}

		popCount += 1
		item := heap.Pop(&nodeFragQueue).(*Item)
		log.Debugf(" POP: [%d][pri:%.2f] %s\n", popCount, item.priority, item.value.Repr())
		nodeFragQueue.show()

		nsPods := tempNodeStatusMap[item.value.NodeName].Pods
		victimPod, victimNodeGpuFrag := sim.findVictimPodOnNodeFragAware(item.value, nodeResMap[item.value.NodeName], nsPods) // evict one pod per node
		if victimPod != nil {
			descheduledPodKeys = append(descheduledPodKeys, utils.GeneratePodKey(victimPod))
			nodeDescheduleCount[item.value.NodeName] += 1
			sim.deletePod(victimPod)

			item.value = *victimNodeGpuFrag
			item.priority = victimNodeGpuFrag.FragAmountSumExceptQ3()
			nodeFragQueue.Push(item) // update the nodeFragQueue
			nodeFragQueue.show()

			oldNode := tempNodeStatusMap[item.value.NodeName].Node                                      // not changed
			newPods := utils.RemovePodFromPodSliceByPod(nsPods, victimPod)                              // remove one pod
			tempNodeStatusMap[item.value.NodeName] = simontype.NodeStatus{Node: oldNode, Pods: newPods} // update the nodeStatus
			numPodsToDeschedule -= 1
		}
	}
	log.Debugf("[DescheduleCluster] nodeDescheduleCount: %v\n", nodeDescheduleCount)
	sim.ClusterAnalysis(TagPostEviction)
	descheduledPod := getPodfromPodMap(descheduledPodKeys, podMap)
	log.Infof("[DescheduleCluster] Num of Descheduled Pods: %d\n", len(descheduledPod))
	return sim.SchedulePods(descheduledPod)
}

func (sim *Simulator) descheduleClusterOnBinPacking(numPodsToDeschedule int, nodeStatus []simontype.NodeStatus,
    nodeResMap map[string]simontype.NodeResource, podMap map[string]*corev1.Pod, gpuPodRatios map[int]float64) []simontype.UnscheduledPod {
    // 按资源需求从大到小排序 Pod
    podList := make([]*corev1.Pod, 0, len(podMap))
    for _, pod := range podMap {
        podList = append(podList, pod)
    }
    sort.Slice(podList, func(i, j int) bool {
        podResI := utils.GetPodResource(podList[i])
        podResJ := utils.GetPodResource(podList[j])
        return (podResI.MilliCpu > podResJ.MilliCpu) || (podResI.MilliCpu == podResJ.MilliCpu && podResI.MilliGpu > podResJ.MilliGpu)
    })

    var descheduledPodKeys []string
    // 为每个 Pod 增加重试次数
    maxRetries := 3

    for _, pod := range podList {
        if numPodsToDeschedule <= 0 {
            break
        }

        retryCount := 0
        for retryCount < maxRetries {
            var bestFitNodeName string
            var minRemainingRes int64 = math.MaxInt64
            podRes := utils.GetPodResource(pod)

            // 计算当前 Pod 需求的 GPU 数量
            podGpuDemand := int(podRes.MilliGpu / 1000) // 假设 MilliGpu 是毫核数，转换为整数个 GPU

            // 根据任务分布调整节点选择的优先级
            var nodePriority map[string]float64 = make(map[string]float64)
            for _, ns := range nodeStatus {
                nodeName := ns.Node.Name
                nodeRes := nodeResMap[nodeName]

                if nodeRes.MilliCpuLeft >= podRes.MilliCpu && canAllocateGpu(nodeRes.MilliGpuLeftList, podRes.MilliGpu) {
                    // 计算分配资源后剩余的总资源
                    remainingGpuList := make([]int64, len(nodeRes.MilliGpuLeftList))
                    copy(remainingGpuList, nodeRes.MilliGpuLeftList)
                    allocateGpu(&remainingGpuList, podRes.MilliGpu)
                    remainingGpu := sum(remainingGpuList)
                    remainingRes := remainingGpu

                    // 根据任务分布计算节点优先级
                    if ratio, ok := gpuPodRatios[podGpuDemand]; ok {
                        // 剩余资源越少，任务占比越高，优先级越高
                        nodePriority[nodeName] = float64(remainingRes) / ratio
                    } else {
                        nodePriority[nodeName] = float64(remainingRes)
                    }

                    // 更新最佳适配节点
                    if int64(nodePriority[nodeName]) < minRemainingRes {
                        minRemainingRes = int64(nodePriority[nodeName])
                        bestFitNodeName = nodeName
                    }
                }
            }

            if bestFitNodeName != "" {
                // 从原节点删除 Pod
                if err := sim.deletePod(pod); err != nil {
                    log.Errorf("[descheduleClusterOnBinPacking] Failed to delete pod(%s) on attempt %d: %v\n",
                        utils.GeneratePodKey(pod), retryCount+1, err)
                } else {
                    descheduledPodKeys = append(descheduledPodKeys, utils.GeneratePodKey(pod))
                    numPodsToDeschedule -= 1
                    // 更新节点资源
                    nodeRes := nodeResMap[bestFitNodeName]
                    nodeRes.MilliCpuLeft -= podRes.MilliCpu
                    allocateGpu(&nodeRes.MilliGpuLeftList, podRes.MilliGpu)
                    nodeResMap[bestFitNodeName] = nodeRes
                    break
                }
            }

            retryCount++
            log.Infof("[descheduleClusterOnBinPacking] Retrying to deschedule pod(%s), attempt %d\n",
                utils.GeneratePodKey(pod), retryCount)
        }
    }

    sim.ClusterAnalysis(TagPostEviction)
    descheduledPod := getPodfromPodMap(descheduledPodKeys, podMap)
    log.Infof("[DescheduleCluster] Num of Descheduled Pods: %d\n", len(descheduledPod))
    return sim.SchedulePods(descheduledPod)
}

// 优化后的辅助函数：计算列表元素的总和
func sum(list []int64) int64 {
	total := int64(0)
	for i := 0; i < len(list); i++ {
		total += list[i]
	}
	return total
}

// 优化后的辅助函数：检查是否可以分配 GPU 资源
func canAllocateGpu(milliGpuLeftList []int64, milliGpuNeeded int64) bool {
	for i := 0; i < len(milliGpuLeftList); i++ {
		if milliGpuLeftList[i] >= milliGpuNeeded {
			return true
		}
	}
	return false
}

// 优化后的辅助函数：分配 GPU 资源
func allocateGpu(milliGpuLeftList *[]int64, milliGpuNeeded int64) {
	for i := 0; i < len(*milliGpuLeftList); i++ {
		if (*milliGpuLeftList)[i] >= milliGpuNeeded {
			(*milliGpuLeftList)[i] -= milliGpuNeeded
			return
		}
	}
}
