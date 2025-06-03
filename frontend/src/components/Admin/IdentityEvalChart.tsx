/**
 * 模型评估数据展示组件
 * 展示不同模型在不同数据集上的评估分数趋势
 */

import React, { useState, useEffect } from "react";
import { Box, Heading, Text, Spinner } from "@chakra-ui/react";
import ReactECharts from "echarts-for-react";
import { IdentityEvalService } from "@/client/sdk.gen";

interface ModelTestResult {
  dataset_key: string;
  dataset_name: string;
  metric: string;
  score: number;
  subset: string;
  num: number;
  date: string;
}

interface ModelData {
  [modelId: string]: ModelTestResult[];
}

interface IdentityEvalChartProps {
  accessToken?: string | null;
  userID?: string | null;
  userRole?: string | null;
}

const IdentityEvalChart: React.FC<IdentityEvalChartProps> = () => {
  const [modelData, setModelData] = useState<ModelData>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDataset] = useState<string>("all");

  // 获取评估数据
  useEffect(() => {
    const fetchEvalData = async () => {
      try {
        setLoading(true);
        const response = await IdentityEvalService.getChartData({});
        setModelData(response as unknown as ModelData);
        setLoading(false);
      } catch (err) {
        console.error("获取评估数据错误:", err);
        setError("获取评估数据时出错");
        setLoading(false);
      }
    };

    fetchEvalData();
  }, []);

  // 生成随机颜色
  const getRandomColor = (() => {
    const colorCache = new Map<string, string>();
    return (key: string) => {
      if (colorCache.has(key)) {
        return colorCache.get(key)!;
      }
      const letters = "0123456789ABCDEF";
      let color = "#";
      for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
      }
      colorCache.set(key, color);
      return color;
    };
  })();

  // 处理图表数据
  const getChartOption = (modelId: string) => {
    const modelResults = modelData[modelId] || [];
    if (modelResults.length === 0) {
      return {};
    }

    // 获取所有日期并排序
    const dates = Array.from(
      new Set(modelResults.map((result) => result.date))
    ).sort((a, b) => new Date(a).getTime() - new Date(b).getTime());

    // 获取所有数据集
    const datasetKeys = Array.from(
      new Set(
        modelResults
          .filter(
            (result) =>
              selectedDataset === "all" ||
              result.dataset_key === selectedDataset
          )
          .map((result) => result.dataset_key)
      )
    );

    const series = datasetKeys.map((datasetKey) => {
      // 为每个数据集创建数据点
      const data = dates.map((date) => {
        const result = modelResults.find(
          (r) => r.dataset_key === datasetKey && r.date === date
        );
        return result ? result.score : null;
      });

      return {
        name: datasetKey,
        type: "line",
        data: data,
        smooth: true,
        symbol: "circle",
        symbolSize: 8,
        itemStyle: {
          color: getRandomColor(datasetKey),
        },
        label: {
          show: true,
          position: "top",
          formatter: "{c}",
          showMinLabel: true,
          showMaxLabel: true,
        },
      };
    });

    return {
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: "cross",
        },
      },
      legend: {
        data: datasetKeys,
        bottom: 0,
      },
      grid: {
        left: "3%",
        right: "4%",
        bottom: "15%",
        top: "10%",
        containLabel: true,
      },
      xAxis: {
        type: "category",
        data: dates.map((date) => {
          const d = new Date(date);
          return `${d.getMonth() + 1}/${d.getDate()}`;
        }),
        boundaryGap: false,
        axisLabel: {
          rotate: 30,
        },
      },
      yAxis: {
        type: "value",
        min: 0,
        max: 1,
        splitLine: {
          show: true,
          lineStyle: {
            type: "dashed",
          },
        },
      },
      series,
    };
  };

  if (loading) {
    return (
      <Box
        p={6}
        borderWidth={1}
        borderRadius="lg"
        boxShadow="md"
        textAlign="center"
      >
        <Spinner />
        <Text mt={2}>加载中...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Box
        p={6}
        borderWidth={1}
        borderRadius="lg"
        boxShadow="md"
        textAlign="center"
      >
        <Text color="red.500">{error}</Text>
      </Box>
    );
  }

  return (
    <Box p={6} borderWidth={1} borderRadius="lg" boxShadow="md">
      <Box mb={6}>
        <Heading size="md">模型评估数据</Heading>
      </Box>
      {Object.keys(modelData).map((modelId) => (
        <Box key={modelId} mb={8}>
          <Heading size="sm" mb={4}>
            {modelId}
          </Heading>
          <Box height="400px">
            <ReactECharts
              option={getChartOption(modelId)}
              style={{ height: "100%", width: "100%" }}
              opts={{ renderer: "svg" }}
            />
          </Box>
        </Box>
      ))}
    </Box>
  );
};

export default IdentityEvalChart;
