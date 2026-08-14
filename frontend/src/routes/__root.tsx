import { createRootRoute, Outlet } from '@tanstack/react-router'
import Layout from '../components/Layout'
import LoginForm from '../components/LoginForm'
import { useAuthStore } from '../stores/authStore'

export const Route = createRootRoute({
  component: RootComponent,
})

function RootComponent() {
  const isAuthenticated = useAuthStore((state) => !!state.token)

  if (!isAuthenticated) {
    return <LoginForm />
  }

  return (
    <Layout>
      <Outlet />
    </Layout>
  )
}
