import { createFileRoute, Outlet } from '@tanstack/react-router'

export const Route = createFileRoute('/channels')({
  component: ChannelsLayout,
})

function ChannelsLayout() {
  return <Outlet />
}
