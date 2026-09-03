import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/channels/$id/plan')({
  beforeLoad: ({ params }) => {
    throw redirect({ to: '/channels/$id', params: { id: params.id }, search: { tab: 'plan' } })
  },
})
