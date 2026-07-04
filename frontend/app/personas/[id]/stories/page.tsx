import { redirect } from "next/navigation";
import { ROUTES } from "@/src/lib/routes";

export default async function PersonaStoriesRedirectPage({
  params
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(ROUTES.personaMemories(id));
}
