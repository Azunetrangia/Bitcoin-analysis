import type { SVGProps } from "react"
const RiskIcon = (props: SVGProps<SVGSVGElement>) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={20} height={20} viewBox="0 0 20 20" fill="none" {...props}>
    <path
      stroke="currentColor"
      strokeWidth="1.667"
      d="M10 1.5L2 5.5v6c0 6 8 6.5 8 6.5s8-.5 8-6.5v-6l-8-4z"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      stroke="currentColor"
      strokeWidth="1.667"
      d="M10 9v3M10 15h.01"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)
export default RiskIcon
