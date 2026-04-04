import { RefreshCw } from "lucide-react"
import { T } from "./DesignTokens"

export const Spinner = () => <span style={{ display: "inline-block", animation: "spin 1s linear infinite", color: T.amber }}><RefreshCw size={14} /></span>
