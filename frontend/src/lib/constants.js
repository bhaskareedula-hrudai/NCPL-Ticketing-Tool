export const TICKET_STATUSES = ["Open", "In Progress", "Pending", "Resolved", "Closed"];
export const TICKET_PRIORITIES = ["Low", "Medium", "High", "Urgent"];

export const STATUS_STYLES = {
  Open:          { bg: "var(--status-active-bg)",   color: "var(--status-active)" },
  "In Progress": { bg: "var(--status-active-bg)",   color: "var(--status-active)" },
  Pending:       { bg: "var(--status-pending-bg)",  color: "var(--status-pending)" },
  Resolved:      { bg: "var(--status-resolved-bg)", color: "var(--status-resolved)" },
  Closed:        { bg: "#EFEFEF",                   color: "#6B6B6B" },
};

export const PRIORITY_STYLES = {
  Low:    { bg: "#F0F9F0", color: "#5CB85C" },
  Medium: { bg: "#EEF5FB", color: "#4A90E2" },
  High:   { bg: "#FDF6EC", color: "#E6A23C" },
  Urgent: { bg: "#FDF0EF", color: "#D9534F" },
};

export const STATUS_CHART_COLORS = {
  Open:          "#4A90E2",
  "In Progress": "#4A90E2",
  Pending:       "#E6A23C",
  Resolved:      "#5CB85C",
  Closed:        "#8C8C8C",
};

export const PRIORITY_CHART_COLORS = {
  Low:    "#5CB85C",
  Medium: "#4A90E2",
  High:   "#E6A23C",
  Urgent: "#D9534F",
};

export const DEPT_COLORS = [
  "#3A4B59", "#4A90E2", "#5CB85C", "#E6A23C", "#D9534F", "#8C8C8C", "#6B5B95",
];
