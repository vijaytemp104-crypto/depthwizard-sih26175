import React from 'react'

export default function ChakraViewLogo({ size = 44, className = '', style = {} }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 40 40"
      fill="none"
      width={size}
      height={size}
      className={className}
      style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
      aria-label="ChakraVIEW Official Emblem"
    >
      <circle cx="20" cy="20" r="18" stroke="#297373" strokeWidth="2.5" strokeDasharray="2 3" opacity="0.4" />
      <circle cx="20" cy="20" r="14" stroke="#297373" strokeWidth="2" />
      <circle cx="20" cy="20" r="8" fill="#297373" fillOpacity="0.1" stroke="#297373" strokeWidth="1.5" />
      <path d="M20 4V12M20 28V36M4 20H12M28 20H36" stroke="#297373" strokeWidth="2" strokeLinecap="round" />
      <path d="M9 9L14 14M26 26L31 31M9 31L14 26M26 14L31 9" stroke="#FF8552" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="20" cy="20" r="3.5" fill="#297373" />
      <circle cx="20" cy="20" r="1.5" fill="#E9D758" />
    </svg>
  )
}
