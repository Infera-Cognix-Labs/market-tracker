export const SeverityBadge = ({ severity }: { severity: string }) => {
  const type = severity === "HIGH" ? "exit" : severity === "MEDIUM" ? "top10" : "info"
  const map: Record<string, string> = { exit: "tag-exit", top10: "tag-top10", info: "tag-info" }
  return <span className={`badge ${map[type]}`}>{severity}</span>
}
