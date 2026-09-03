import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/channels/$id/edit')({
  beforeLoad: ({ params }) => {
    throw redirect({ to: '/channels/$id', params: { id: params.id }, search: { tab: 'config' } })
  },
})
