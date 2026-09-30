export function Logo({ size = 'sm', as: Tag = 'span', className = '', ...rest }) {
  return (
    <Tag className={`logo logo-${size} ${className}`.trim()} {...rest}>
      MSG
    </Tag>
  )
}
