/* A single column with no side navigation — each screen brings its own
   header, which is where the navigation lives. */
export function Shell({ children }) {
  return <div className="frame">{children}</div>
}
