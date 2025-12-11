import type { SVGProps } from "react"
const ChartIcon = (props: SVGProps<SVGSVGElement>) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={20} height={20} viewBox="0 0 20 20" fill="none" {...props}>
    <path
      stroke="currentColor"
      strokeWidth="1.667"
      d="M2 16h16M4 12v4M8 8v8M12 6v10M16 4v12"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)
export default ChartIcon
