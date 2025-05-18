import { 
  Box,
  Button,
  Flex, 
  Heading, 
  Spinner, 
  Text
} from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { FiPause, FiPlay } from "react-icons/fi"

import { SchedulerService } from "@/client"
import type { JobInfo } from "@/client/types.gen"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/scheduler")({
  component: SchedulerPage,
})

function SchedulerPage() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  // 获取所有定时任务
  const {
    data: jobs,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["scheduler", "jobs"],
    queryFn: () => SchedulerService.getAllJobs(),
  })

  // 暂停任务的mutation
  const pauseJobMutation = useMutation({
    mutationFn: (jobId: string) => SchedulerService.pauseJob({ jobId }),
    onSuccess: () => {
      showSuccessToast("任务已暂停")
      // 刷新任务列表
      queryClient.invalidateQueries({ queryKey: ["scheduler", "jobs"] })
    },
    onError: (error) => {
      showErrorToast(`暂停任务失败: ${String(error)}`)
    },
  })

  // 恢复任务的mutation
  const resumeJobMutation = useMutation({
    mutationFn: (jobId: string) => SchedulerService.resumeJob({ jobId }),
    onSuccess: () => {
      showSuccessToast("任务已恢复")
      // 刷新任务列表
      queryClient.invalidateQueries({ queryKey: ["scheduler", "jobs"] })
    },
    onError: (error) => {
      showErrorToast(`恢复任务失败: ${String(error)}`)
    },
  })

  // 处理暂停或恢复任务
  const handleToggleJob = (job: JobInfo) => {
    // 通过判断下次执行时间是否存在来确定任务是暂停还是运行状态
    const isPaused = !job.next_run_time

    if (isPaused) {
      resumeJobMutation.mutate(job.id)
    } else {
      pauseJobMutation.mutate(job.id)
    }
  }

  // 获取触发器类型的中文名称
  const getTriggerTypeName = (trigger: string) => {
    const triggerTypeMap: Record<string, string> = {
      interval: "间隔触发",
      cron: "定时触发",
      date: "日期触发",
    }
    return triggerTypeMap[trigger] || trigger
  }

  // 格式化触发器参数
  const formatTriggerArgs = (
    trigger: string,
    args: Record<string, unknown>,
  ) => {
    if (trigger === "interval") {
      // 处理间隔触发器
      if (typeof args.seconds === "number") {
        const seconds = args.seconds
        if (seconds % 86400 === 0) return `${seconds / 86400}天`
        if (seconds % 3600 === 0) return `${seconds / 3600}小时`
        if (seconds % 60 === 0) return `${seconds / 60}分钟`
        return `${seconds}秒`
      }
      return JSON.stringify(args)
    }
    if (trigger === "cron") {
      // 处理Cron触发器
      return `${args.hour || "*"}:${args.minute || "*"}:${args.second || "*"}`
    }
    if (trigger === "date") {
      // 处理日期触发器
      return JSON.stringify(args)
    }
    return JSON.stringify(args)
  }

  if (isLoading) {
    return (
      <Flex justify="center" align="center" h="50vh">
        <Spinner size="xl" />
      </Flex>
    )
  }

  if (isError) {
    return (
      <Flex direction="column" align="center" py={10}>
        <Heading size="md" mb={4}>
          加载定时任务失败
        </Heading>
        <Text color="red.500">{String(error)}</Text>
      </Flex>
    )
  }

  return (
    <Flex direction="column" width="100%" p={4}>
      <Heading as="h1" size="lg" mb={6}>
        定时任务管理
      </Heading>

      {jobs && jobs.length > 0 ? (
        jobs.map((job) => {
          const isPaused = !job.next_run_time

          return (
            <Box key={job.id} mb={4} p={4} borderWidth="1px" borderRadius="md">
              <Flex pb={2} justify="space-between" align="center">
                <Heading size="md">{job.name}</Heading>
                <Button
                  colorScheme={isPaused ? "green" : "orange"}
                  size="sm"
                  onClick={() => handleToggleJob(job)}
                  loading={
                    pauseJobMutation.isPending || resumeJobMutation.isPending
                  }
                >
                  {isPaused ? (
                    <>
                      <FiPlay style={{ marginRight: "0.5rem" }} /> 恢复
                    </>
                  ) : (
                    <>
                      <FiPause style={{ marginRight: "0.5rem" }} /> 暂停
                    </>
                  )}
                </Button>
              </Flex>
              <Box>
                <Text mb={2}>
                  <Text as="span" fontWeight="bold">
                    触发器类型:{" "}
                  </Text>
                  {getTriggerTypeName(job.trigger)}
                </Text>
                <Text mb={2}>
                  <Text as="span" fontWeight="bold">
                    触发器参数:{" "}
                  </Text>
                  {formatTriggerArgs(job.trigger, job.trigger_args)}
                </Text>
                <Text>
                  <Text as="span" fontWeight="bold">
                    下次执行时间:{" "}
                  </Text>
                  {job.next_run_time ? job.next_run_time : "已暂停"}
                </Text>
              </Box>
            </Box>
          )
        })
      ) : (
        <Text>没有找到定时任务</Text>
      )}
    </Flex>
  )
} 