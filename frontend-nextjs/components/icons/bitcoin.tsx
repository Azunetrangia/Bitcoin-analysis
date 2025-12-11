import type { SVGProps } from "react"
const BitcoinIcon = (props: SVGProps<SVGSVGElement>) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={20} height={20} viewBox="0 0 20 20" fill="none" {...props}>
    <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.667" />
    <path
      d="M10 5V15M8 7.5C8 6.5 8.8 6 10 6C11.2 6 12 6.5 12 7.5C12 8.2 11.5 8.7 10.8 8.9M8 12.5C8 13.5 8.8 14 10 14C11.3 14 12 13.3 12 12.5C12 11.6 11.2 11 10.5 10.8"
      stroke="currentColor"
      strokeWidth="1.667"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)
export default BitcoinIcon
