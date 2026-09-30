import { Bubble } from '../components/Bubble'
import { Logo } from '../components/Logo'
import { Link } from '../lib/router'

export function Welcome() {
  return (
    <div className="welcome on-ink">
      <div className="welcome-body">
        <div>
          <Logo size="lg" as="h1" className="welcome-mark" />
          <p className="welcome-lead">
            A messenger for two people at a time. You need one username to start, and
            messages land the moment they are sent.
          </p>
          <div className="welcome-actions">
            <Link to="/signup" className="btn btn-invert">
              Create an account
            </Link>
            <Link to="/login" className="btn btn-quiet">
              Log in
            </Link>
          </div>
        </div>

        <div className="welcome-thread" aria-hidden="true">
          <Bubble>no groups?</Bubble>
          <Bubble mine>no groups.</Bubble>
          <Bubble>no feed?</Bubble>
          <Bubble mine>no feed. just you and whoever you asked for.</Bubble>
        </div>
      </div>

      <footer className="welcome-foot">
        <span>Built by Ayo-Ajayi Oluwatokiloba</span>
        <span>Messages are held on your own server.</span>
      </footer>
    </div>
  )
}
