import { createFileRoute, Navigate } from '@tanstack/react-router'
import { useAuthStore } from '../stores/authStore'
import LoginForm from '../components/LoginForm'

export const Route = createFileRoute('/login')({
  component: LoginPage,
})

function LoginPage() {
  const isAuthenticated = useAuthStore((state) => !!state.token)

  if (isAuthenticated) {
    return <Navigate to="/" />
  }

  return <LoginForm />
}
