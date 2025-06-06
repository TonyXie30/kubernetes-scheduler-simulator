package plugin

import (
	"context"
	"fmt"
	"strconv"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	resourcehelper "k8s.io/kubectl/pkg/util/resource"
	"k8s.io/kubernetes/pkg/scheduler/framework"

	simontype "github.com/hkust-adsl/kubernetes-scheduler-simulator/pkg/type"
	gpushareutils "github.com/hkust-adsl/kubernetes-scheduler-simulator/pkg/type/open-gpu-share/utils"
	"github.com/hkust-adsl/kubernetes-scheduler-simulator/pkg/utils"
)

type FGDScorePlugin struct {
	handle      framework.Handle
	typicalPods *simontype.TargetPodList
	podDistribution map[int]float64	
}

var _ framework.ScorePlugin = &FGDScorePlugin{}

func NewFGDScorePlugin(_ runtime.Object, handle framework.Handle, typicalPods *simontype.TargetPodList, podDistributionConfig map[int]float64) (framework.Plugin, error) {
	plugin := &FGDScorePlugin{
		handle:      handle,
		typicalPods: typicalPods,
		podDistribution: podDistributionConfig,
	}
	allocateGpuIdFunc[plugin.Name()] = func(nodeRes simontype.NodeResource, podRes simontype.PodResource, cfg simontype.GpuPluginCfg, typicalPods *simontype.TargetPodList) (gpuId string) {
		return allocateGpuIdBasedOnFGDScore(nodeRes, podRes, cfg, typicalPods, plugin.podDistribution)
	}
	return plugin, nil
}

func (plugin *FGDScorePlugin) Name() string {
	return simontype.FGDScorePluginName
}

func (plugin *FGDScorePlugin) Score(ctx context.Context, state *framework.CycleState, p *v1.Pod, nodeName string) (int64, *framework.Status) {
	if podReq, _ := resourcehelper.PodRequestsAndLimits(p); len(podReq) == 0 {
		return framework.MaxNodeScore, framework.NewStatus(framework.Success)
	}

	nodeResPtr := utils.GetNodeResourceViaHandleAndName(plugin.handle, nodeName)
	if nodeResPtr == nil {
		return framework.MinNodeScore, framework.NewStatus(framework.Error, fmt.Sprintf("failed to get nodeRes(%s)\n", nodeName))
	}
	nodeRes := *nodeResPtr

	podRes := utils.GetPodResource(p)
	if !utils.IsNodeAccessibleToPod(nodeRes, podRes) {
		return framework.MinNodeScore, framework.NewStatus(framework.Error, fmt.Sprintf("Node (%s) %s does not match GPU type request of pod %s\n", nodeName, nodeRes.Repr(), podRes.Repr()))
	}

	score, _ := calculateGpuShareFragExtendScore(nodeRes, podRes, plugin.typicalPods, plugin.podDistribution)
	return score, framework.NewStatus(framework.Success)
}

func (plugin *FGDScorePlugin) ScoreExtensions() framework.ScoreExtensions {
	return nil
}

// FGD计算实现,包含partial实现和完整GPU实现
func calculateGpuShareFragExtendScore(nodeRes simontype.NodeResource, podRes simontype.PodResource, typicalPods *simontype.TargetPodList, podDistribution map[int]float64) (score int64, gpuId string) {
	nodeGpuShareFragScore := utils.NodeGpuShareFragAmountScore(nodeRes, *typicalPods, podDistribution)
	if podRes.GpuNumber == 1 && podRes.MilliGpu < gpushareutils.MILLI { // request partial GPU
		score, gpuId = 0, ""
		for i := 0; i < len(nodeRes.MilliGpuLeftList); i++ {
			if nodeRes.MilliGpuLeftList[i] >= podRes.MilliGpu {
				newNodeRes := nodeRes.Copy()
				newNodeRes.MilliCpuLeft -= podRes.MilliCpu
				newNodeRes.MilliGpuLeftList[i] -= podRes.MilliGpu
				newNodeGpuShareFragScore := utils.NodeGpuShareFragAmountScore(newNodeRes, *typicalPods, podDistribution)
				fragScore := int64(sigmoid((nodeGpuShareFragScore-newNodeGpuShareFragScore)/1000) * float64(framework.MaxNodeScore))
				if gpuId == "" || fragScore > score {
					score = fragScore
					gpuId = strconv.Itoa(i)
				}
			}
		}
		return score, gpuId
	} else {
		newNodeRes, _ := nodeRes.Sub(podRes)
		newNodeGpuShareFragScore := utils.NodeGpuShareFragAmountScore(newNodeRes, *typicalPods, podDistribution)
		return int64(sigmoid((nodeGpuShareFragScore-newNodeGpuShareFragScore)/1000) * float64(framework.MaxNodeScore)), simontype.AllocateExclusiveGpuId(nodeRes, podRes)
	}
}

func allocateGpuIdBasedOnFGDScore(nodeRes simontype.NodeResource, podRes simontype.PodResource, _ simontype.GpuPluginCfg, typicalPods *simontype.TargetPodList, podDistribution map[int]float64) (gpuId string) {
	_, gpuId = calculateGpuShareFragExtendScore(nodeRes, podRes, typicalPods, podDistribution)
	return gpuId
}
