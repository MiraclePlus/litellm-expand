import { createFileRoute } from "@tanstack/react-router";
import { Container } from "@chakra-ui/react";
import { ModelEvalConfig } from "../../components/Admin/ModelEvalConfig";

export const Route = createFileRoute("/_layout/model-eval-config")({
  component: ModelEvalConfigPage,
});

function ModelEvalConfigPage() {
  return (
    <Container maxW="container.xl" py={6}>
      <ModelEvalConfig />
    </Container>
  );
} 