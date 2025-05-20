import { createFileRoute } from "@tanstack/react-router";
import { Container } from "@chakra-ui/react";
import IdentityEvalChart from "@/components/Admin/IdentityEvalChart";

export const Route = createFileRoute("/_layout/identity-eval-chart")({
  component: IdentityEvalChartPage,
});

function IdentityEvalChartPage() {
  return (
    <Container maxW="container.xl" py={6}>
      <IdentityEvalChart />
    </Container>
  );
}
