const NAV_LINKS = ['Story', 'Investing', 'Building', 'Advisory']

export default function Navbar() {
  return (
    <div className="px-6 md:px-12 lg:px-16 pt-6">
      <nav className="liquid-glass rounded-xl px-4 py-2 flex items-center justify-between">
        <div className="text-2xl font-semibold tracking-tight text-white">
          VEX
        </div>

        <div className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map((link) => (
            <a
              key={link}
              href="#"
              className="text-sm text-white transition-colors hover:text-gray-300"
            >
              {link}
            </a>
          ))}
        </div>

        <button
          type="button"
          className="bg-white text-black px-6 py-2 rounded-lg text-sm font-medium transition-colors hover:bg-gray-100"
        >
          Start a Chat
        </button>
      </nav>
    </div>
  )
}
