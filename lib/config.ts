import { ColorScheme, StartScreenPrompt, ThemeOption } from "@openai/chatkit";

export const WORKFLOW_ID =
  process.env.NEXT_PUBLIC_CHATKIT_WORKFLOW_ID?.trim() ?? "";

export const WORKFLOW_ID_2 =
  process.env.NEXT_PUBLIC_CHATKIT_WORKFLOW_ID_2?.trim() ?? "";

export const WORKFLOW_ID_3 =
  process.env.NEXT_PUBLIC_CHATKIT_WORKFLOW_ID_3?.trim() ?? "";

export type WorkflowConfig = {
  id: string;
  name: string;
  icon: string;
};

export const WORKFLOWS: WorkflowConfig[] = [
  {
    id: WORKFLOW_ID_2,
    name: "내부 지식 문의",
    icon: "book-open",
  },
  {
    id: WORKFLOW_ID_3,
    name: "팩트 워크플로우",
    icon: "lightbulb",
  },
];

export const CREATE_SESSION_ENDPOINT = "/api/create-session";

export const STARTER_PROMPTS: StartScreenPrompt[] = [
  {
    label: "What can you do?",
    prompt: "What can you do?",
    icon: "circle-question",
  },
];

export const PLACEHOLDER_INPUT = "Ask anything...";

export const GREETING = "How can I help you today?";

export const getThemeConfig = (theme: ColorScheme): ThemeOption => ({
  color: {
    grayscale: {
      hue: 220,
      tint: 6,
      shade: theme === "dark" ? -1 : -4,
    },
    accent: {
      primary: theme === "dark" ? "#f1f5f9" : "#0f172a",
      level: 1,
    },
  },
  radius: "round",
  // Add other theme options here
  // chatkit.studio/playground to explore config options
});
