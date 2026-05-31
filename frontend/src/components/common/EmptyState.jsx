import React from "react";

export default function EmptyState({ title, description, action }) {
  return (
    <div className="p-16 text-center">
      <div className="mono-label mb-2">{title}</div>
      {description && (
        <p className="text-sm mb-4" style={{ color: "var(--text-secondary)" }}>
          {description}
        </p>
      )}
      {action}
    </div>
  );
}
