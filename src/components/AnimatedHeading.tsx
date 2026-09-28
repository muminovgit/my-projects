import { useEffect, useState, type CSSProperties } from 'react'

interface AnimatedHeadingProps {
  text: string
  initialDelay?: number
  className?: string
  style?: CSSProperties
}

const CHAR_DELAY = 30

export default function AnimatedHeading({
  text,
  initialDelay = 200,
  className = '',
  style,
}: AnimatedHeadingProps) {
  const [started, setStarted] = useState(false)
  const lines = text.split('\n')

  useEffect(() => {
    const timer = setTimeout(() => setStarted(true), initialDelay)
    return () => clearTimeout(timer)
  }, [initialDelay])

  return (
    <h1 className={className} style={style}>
      {lines.map((line, lineIndex) => (
        <span key={lineIndex} className="block">
          {line.split('').map((char, charIndex) => {
            const delay =
              lineIndex * line.length * CHAR_DELAY + charIndex * CHAR_DELAY
            return (
              <span
                key={charIndex}
                className="inline-block transition-all ease-out"
                style={{
                  opacity: started ? 1 : 0,
                  transform: started ? 'translateX(0)' : 'translateX(-18px)',
                  transitionDelay: `${delay}ms`,
                  transitionDuration: '500ms',
                }}
              >
                {char === ' ' ? ' ' : char}
              </span>
            )
          })}
        </span>
      ))}
    </h1>
  )
}
