import { BookOpen, Lightbulb, ChevronDown, Loader2 } from "lucide-react";

type IconName = "book-open" | "lightbulb" | "chevron-down" | "loader";

type IconProps = {
  name: IconName;
  size?: number;
  className?: string;
};

export function Icon({ name, size = 20, className = "" }: IconProps) {
  const iconProps = { size, className };

  switch (name) {
    case "book-open":
      return <BookOpen {...iconProps} />;
    case "lightbulb":
      return <Lightbulb {...iconProps} />;
    case "chevron-down":
      return <ChevronDown {...iconProps} />;
    case "loader":
      return <Loader2 {...iconProps} />;
    default:
      return null;
  }
}

// Backward compatibility
export function WorkflowIcon({ icon, size = 20, className = "" }: { icon: string; size?: number; className?: string }) {
  return <Icon name={icon as IconName} size={size} className={className} />;
}
