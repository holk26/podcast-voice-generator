interface AudioPlayerProps {
  src: string
}

export default function AudioPlayer({ src }: AudioPlayerProps) {
  return (
    <audio key={src} controls src={src} className="w-full mt-2">
      Tu navegador no soporta audio.
    </audio>
  )
}
