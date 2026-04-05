interface Props {
  count: number | string | undefined
}

export default function CreditBadge({ count }: Props) {
  const isZero = count === 0
  return (
    <span className={`credit-badge${isZero ? ' zero' : ''}`}>
      {count === '∞' ? '∞' : count ?? '—'}
    </span>
  )
}
