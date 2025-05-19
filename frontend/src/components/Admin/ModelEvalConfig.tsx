import { useState, useEffect } from 'react';
import {
  Box,
  Flex,
  Heading,
  Spinner,
  Table,
} from '@chakra-ui/react';
import { IdentityEvalModelService } from '../../client/sdk.gen';
import useCustomToast from '../../hooks/useCustomToast';
import { Checkbox } from '../../components/ui/checkbox';

// 固定的数据集键
const DATASET_KEYS = [
  'AIME24',
  'AIME25',
  'GPQA_DIAMOND',
  'MMLU_PRO_LAW',
  'MMLU_PRO_BUSINESS',
  'MMLU_PRO_PHILOSOPHY',
  'LIVE_CODE_BENCH'
];

interface ModelConfig {
  ai_model_id: string;
  dataset_keys: string[];
  created_at: string;
  updated_at: string;
}

export const ModelEvalConfig = () => {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const { showSuccessToast, showErrorToast } = useCustomToast();

  // 加载所有模型配置
  const loadModels = async () => {
    setLoading(true);
    try {
      const modelData = await IdentityEvalModelService.getAllModels();
      setModels(modelData.map(m => ({
        ai_model_id: m.ai_model_id || '',
        dataset_keys: m.dataset_keys || [],
        created_at: m.created_at || '',
        updated_at: m.updated_at || ''
      })));
    } catch (error) {
      console.error('Failed to load models:', error);
      showErrorToast('无法获取模型配置数据');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadModels();
  }, []);

  // 切换数据集勾选状态
  const toggleDatasetKey = async (modelId: string, datasetKey: string) => {
    const model = models.find(m => m.ai_model_id === modelId);
    if (!model) return;

    // 创建新的数据集键数组
    let newDatasetKeys: string[];
    if (model.dataset_keys.includes(datasetKey)) {
      // 如果已经包含，则移除
      newDatasetKeys = model.dataset_keys.filter(key => key !== datasetKey);
    } else {
      // 如果不包含，则添加
      newDatasetKeys = [...model.dataset_keys, datasetKey];
    }

    // 更新UI状态
    setModels(models.map(m => 
      m.ai_model_id === modelId ? { ...m, dataset_keys: newDatasetKeys } : m
    ));

    // 保存到服务器
    setSaving(prev => ({ ...prev, [modelId]: true }));
    try {
      await IdentityEvalModelService.updateDatasetKeys({
        aiModelId: modelId,
        requestBody: newDatasetKeys
      });
      showSuccessToast(`已更新模型 ${modelId} 的配置`);
    } catch (error) {
      console.error('Failed to update model:', error);
      showErrorToast(`更新模型 ${modelId} 配置时出错`);
      // 恢复原来的状态
      loadModels();
    } finally {
      setSaving(prev => ({ ...prev, [modelId]: false }));
    }
  };

  // 删除模型
  // const deleteModel = async (modelId: string) => {
  //   try {
  //     await IdentityEvalModelService.deleteModel(modelId);
  //     setModels(models.filter(m => m.ai_model_id !== modelId));
  //     showSuccessToast(`模型 ${modelId} 已删除`);
  //   } catch (error) {
  //     console.error('Failed to delete model:', error);
  //     showErrorToast(`删除模型 ${modelId} 时出错`);
  //   }
  // };

  if (loading) {
    return (
      <Flex justify="center" align="center" height="400px">
        <Spinner size="xl" />
      </Flex>
    );
  }

  return (
    <Box>
      <Heading size="lg" mb={6}>评测模型配置</Heading>
      
      {/* 模型配置表格 */}
      <Box 
        overflowX="auto" 
        borderWidth="1px" 
        borderRadius="lg" 
        borderColor="gray.200" 
        bg="white"
        boxShadow="sm"
      >
        <Table.Root size={{ base: "sm", md: "md" }}>
          <Table.Header>
            <Table.Row>
              <Table.ColumnHeader>模型ID</Table.ColumnHeader>
              {DATASET_KEYS.map(key => (
                <Table.ColumnHeader key={key} textAlign="center">{key}</Table.ColumnHeader>
              ))}
              {/* <Table.ColumnHeader>操作</Table.ColumnHeader> */}
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {models.map(model => (
              <Table.Row key={model.ai_model_id}>
                <Table.Cell fontWeight="medium">{model.ai_model_id}</Table.Cell>
                {DATASET_KEYS.map(datasetKey => (
                  <Table.Cell key={datasetKey} textAlign="center">
                    <Checkbox 
                      checked={model.dataset_keys.includes(datasetKey)}
                      onChange={() => toggleDatasetKey(model.ai_model_id, datasetKey)}
                      disabled={saving[model.ai_model_id]}
                    />
                  </Table.Cell>
                ))}
                {/* <Table.Cell>
                  <IconButton
                    aria-label="删除模型"
                    colorScheme="red"
                    variant="ghost"
                    onClick={() => deleteModel(model.ai_model_id)}
                    size="sm"
                  >
                    <FiTrash2 />
                  </IconButton>
                </Table.Cell> */}
              </Table.Row>
            ))}
            {models.length === 0 && (
              <Table.Row>
                <Table.Cell colSpan={DATASET_KEYS.length + 2} textAlign="center" py={4}>
                  暂无模型配置
                </Table.Cell>
              </Table.Row>
            )}
          </Table.Body>
        </Table.Root>
      </Box>
    </Box>
  );
}; 