import type { SVGProps } from "react"
const TrendingIcon = (props: SVGProps<SVGSVGElement>) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={20} height={20} viewBox="0 0 20 20" fill="none" {...props}>
    <path
      stroke="currentColor"
      strokeWidth="1.667"
      d="M2 18h16M4 10l4-4 4 4 4-6"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path stroke="currentColor" strokeWidth="1.667" d="M14 4h4v4" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)
export default TrendingIcon
