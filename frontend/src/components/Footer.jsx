export default function Footer() {
  return (
    <footer className="mt-16 border-t border-line">
      <div className="container-page py-8 text-xs leading-relaxed text-mute">
        <p>CineMatch is a college project for discovering Indian cinema.</p>
        <p className="mt-1">
          This product uses the TMDB API but is not endorsed or certified by TMDB. Streaming
          availability data is provided through TMDB (powered by JustWatch). Ratings shown are
          labelled with their source.
        </p>
      </div>
    </footer>
  )
}