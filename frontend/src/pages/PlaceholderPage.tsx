import { EmptyState } from "../components/EmptyState";

type PlaceholderPageProps = {
  title: string;
};

export function PlaceholderPage({ title }: PlaceholderPageProps) {
  return <EmptyState title={`${title} is empty`} description="This workspace is ready for the next Phase 1 implementation slice." />;
}
