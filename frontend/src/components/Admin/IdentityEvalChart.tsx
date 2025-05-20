/**
 * 模型评估数据展示组件
 * 展示不同模型在不同数据集上的评估分数趋势
 */

import React, { useState, useEffect } from "react";
import { Box, Heading, Text, Spinner } from "@chakra-ui/react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";

import { IdentityEvalService } from "@/client/sdk.gen";

// 注册 Chart.js 组件
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface ModelTestResult {
  id: number;
  model_id: string;
  dataset_key: string;
  dataset_name: string;
  metric: string;
  score: number;
  subset: string;
  num: number;
  date: string;
  created_at: string;
  updated_at: string;
}

interface IdentityEvalData {
  [date: string]: ModelTestResult[];
}

interface IdentityEvalChartProps {
  accessToken?: string | null;
  userID?: string | null;
  userRole?: string | null;
}

const IdentityEvalChart: React.FC<IdentityEvalChartProps> = () => {
  const [evalData, setEvalData] = useState<IdentityEvalData>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<string>("all");

  // 获取评估数据
  useEffect(() => {
    const fetchEvalData = async () => {
      try {
        setLoading(true);

        const response = await IdentityEvalService.getChartData({});
        // 将API返回的数据转换为正确的类型
        const formattedData: IdentityEvalData = {};
        Object.entries(response).forEach(([date, results]) => {
          formattedData[date] = (results as unknown as ModelTestResult[]).map(
            (result) => ({
              id: result.id,
              model_id: result.model_id,
              dataset_key: result.dataset_key,
              dataset_name: result.dataset_name,
              metric: result.metric,
              score: result.score,
              subset: result.subset,
              num: result.num,
              date: result.date,
              created_at: result.created_at,
              updated_at: result.updated_at,
            })
          );
        });
        setEvalData(formattedData);
        setLoading(false);
      } catch (err) {
        console.error("获取评估数据错误:", err);
        setError("获取评估数据时出错");
        setLoading(false);
      }
    };

    fetchEvalData();
  }, []);

  // 处理图表数据
  const processChartData = (modelId: string) => {
    const chartData = {
      labels: [] as string[],
      datasets: [] as {
        label: string;
        data: number[];
        borderColor: string;
        backgroundColor: string;
        tension: number;
      }[],
    };

    if (Object.keys(evalData).length === 0) {
      return chartData;
    }

    // 获取排序后的日期
    const sortedDates = Object.keys(evalData).sort(
      (a, b) => new Date(a).getTime() - new Date(b).getTime()
    );
    chartData.labels = sortedDates.map((date) => {
      const d = new Date(date);
      return `${d.getMonth() + 1}/${d.getDate()}`;
    });

    // 为每个数据集创建系列
    const datasetMap = new Map<
      string,
      {
        label: string;
        data: number[];
        borderColor: string;
        backgroundColor: string;
      }
    >();

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

    // 遍历数据创建数据集
    sortedDates.forEach((date, dateIndex) => {
      const dateResults = evalData[date] || [];
      dateResults.forEach((result: ModelTestResult) => {
        if (
          result.model_id === modelId &&
          (selectedDataset === "all" || result.dataset_key === selectedDataset)
        ) {
          if (!datasetMap.has(result.dataset_key)) {
            const color = getRandomColor(result.dataset_key);
            datasetMap.set(result.dataset_key, {
              label: result.dataset_key,
              data: Array(sortedDates.length).fill(null),
              borderColor: color,
              backgroundColor: color,
            });
          }
          const dataset = datasetMap.get(result.dataset_key);
          if (dataset) {
            dataset.data[dateIndex] = result.score;
          }
        }
      });
    });

    chartData.datasets = Array.from(datasetMap.values()).map((dataset) => ({
      ...dataset,
      tension: 0.4,
    }));

    return chartData;
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

  // 获取所有唯一的模型ID
  const modelIds = Array.from(
    new Set(
      Object.values(evalData).flatMap((results: any) =>
        results.map((result: any) => result.model_id)
      )
    )
  );

  return (
    <Box p={6} borderWidth={1} borderRadius="lg" boxShadow="md">
      <Box mb={6}>
        <Heading size="md">模型评估数据</Heading>
      </Box>
      {modelIds.map((modelId) => (
        <Box key={modelId} mb={8}>
          <Heading size="sm" mb={4}>
            {modelId}
          </Heading>
          <Box height="400px">
            <Line
              data={processChartData(modelId)}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: "bottom" as const,
                  },
                  title: {
                    display: true,
                    text: `模型 ${modelId} 评估分数趋势`,
                  },
                },
                scales: {
                  y: {
                    min: 0,
                    max: 1,
                  },
                },
              }}
            />
          </Box>
        </Box>
      ))}
    </Box>
  );
};

export default IdentityEvalChart;
