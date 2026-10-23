
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type Dish = {
  id: number
  name: string
  average_rating: number | null
  rating_count: number
}

type MenuResponse = {
  weekday: number
  meal_type: string
  dishes: Dish[]
}

type Meal = 'breakfast' | 'lunch' | 'dinner'

type LoginResponse = {
  access_token: string
  token_type: string
}

const meals: Meal[] = ['breakfast', 'lunch', 'dinner']
const API_URL = 'http://127.0.0.1:8000'

function App() {
  const [menu, setMenu] = useState<MenuResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedMeal, setSelectedMeal] = useState<Meal>('breakfast')

  const [selectedRatings, setSelectedRatings] = useState<
    Record<number, number>
  >({})

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [accessToken, setAccessToken] = useState<string | null>(
    () => localStorage.getItem('access_token'),
  )
  const [authMessage, setAuthMessage] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)

  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [name, setName] = useState('')

  useEffect(() => {
    async function fetchMenu() {
      try {
        setLoading(true)
        setError(null)

        const response = await fetch(
          `${API_URL}/menus/today/${selectedMeal}`,
        )

        if (!response.ok) {
          throw new Error(`Request failed: ${response.status}`)
        }

        const data: MenuResponse = await response.json()
        setMenu(data)
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Something went wrong',
        )
      } finally {
        setLoading(false)
      }
    }

    fetchMenu()
  }, [selectedMeal])

  async function handleRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAuthMessage('')
    setLoginLoading(true)

    try {
      const response = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, email, password }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'Registration failed. Please check your details.',
        )
      }

      setAuthMessage('Account created successfully. Please log in.')
      setAuthMode('login')
      setName('')
      setPassword('')
    } catch (err) {
      setAuthMessage(
        err instanceof Error ? err.message : 'Something went wrong.',
      )
    } finally {
      setLoginLoading(false)
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAuthMessage('')
    setLoginLoading(true)

    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      })

      if (!response.ok) {
        throw new Error('Login failed. Check your email and password.')
      }

      const data: LoginResponse = await response.json()

      localStorage.setItem('access_token', data.access_token)
      setAccessToken(data.access_token)
      setPassword('')
      setAuthMessage('Logged in successfully.')
    } catch (err) {
      setAuthMessage(
        err instanceof Error ? err.message : 'Something went wrong.',
      )
    } finally {
      setLoginLoading(false)
    }
  }

  function handleLogout() {
    localStorage.removeItem('access_token')
    setAccessToken(null)
    setAuthMessage('')
  }

  async function handleRatingSubmit(dishId: number) {
    const score = selectedRatings[dishId]

    if (!score) return

    if (!accessToken) {
      setAuthMessage('Please log in before submitting a rating.')
      return
    }

    setAuthMessage('')

    try {
      const response = await fetch(`${API_URL}/ratings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          dish_id: dishId,
          score,
        }),
      })

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('access_token')
          setAccessToken(null)
          throw new Error('Your session expired. Please log in again.')
        }

        const detail = await response.json().catch(() => null)
        throw new Error(
          detail?.detail ?? `Rating submission failed: ${response.status}`,
        )
      }

      setAuthMessage('Rating submitted successfully.')

      // Refresh the menu so updated averages and counts can appear.
      const menuResponse = await fetch(
        `${API_URL}/menus/today/${selectedMeal}`,
      )

      if (menuResponse.ok) {
        const updatedMenu: MenuResponse = await menuResponse.json()
        setMenu(updatedMenu)
      }
    } catch (err) {
      setAuthMessage(
        err instanceof Error ? err.message : 'Could not submit rating.',
      )
    }
  }

  return (
    <main className="app">
      <header className="header">
        <h1>
          DataMess<span>.</span>
        </h1>
        <p>Your campus mess menu, in one place.</p>
      </header>

      <section className="auth-section">
        {accessToken ? (
          <div className="auth-card">
            <h2>You're logged in</h2>
            <p>You can now rate dishes.</p>
            <button
              type="button"
              className="logout-button"
              onClick={handleLogout}
            >
              Log out
            </button>
          </div>
        ) : (
          <div className="auth-card">
            <div className="auth-heading">
              <p className="eyebrow">YOUR DATAMESS ACCOUNT</p>
              <h2>
                {authMode === 'login' ? 'Welcome back' : 'Create your account'}
              </h2>
              <p>
                {authMode === 'login'
                  ? 'Log in to rate your mess dishes.'
                  : 'Join DataMess and share your ratings.'}
              </p>
            </div>

            <div className="auth-tabs">
              <button
                type="button"
                className={authMode === 'login' ? 'auth-tab active' : 'auth-tab'}
                onClick={() => {
                  setAuthMode('login')
                  setAuthMessage('')
                }}
              >
                Login
              </button>
              <button
                type="button"
                className={authMode === 'register' ? 'auth-tab active' : 'auth-tab'}
                onClick={() => {
                  setAuthMode('register')
                  setAuthMessage('')
                }}
              >
                Register
              </button>
            </div>

            <form
              className="auth-form"
              onSubmit={authMode === 'login' ? handleLogin : handleRegister}
            >
              {authMode === 'register' && (
                <label>
                  Full name
                  <input
                    type="text"
                    placeholder="Enter your name"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    required
                  />
                </label>
              )}

              <label>
                Email address
                <input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </label>

              <label>
                Password
                <input
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
              </label>

              <button
                className="auth-submit"
                type="submit"
                disabled={loginLoading}
              >
                {loginLoading
                  ? 'Please wait...'
                  : authMode === 'login'
                    ? 'Log in'
                    : 'Create account'}
              </button>
            </form>

            {authMessage && (
              <p className="auth-message" role="status">
                {authMessage}
              </p>
            )}
          </div>
        )}
      </section>

      <section className="menu-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">NIT PATNA · BOYS' MESS</p>
            <h2>Today's Menu</h2>
          </div>

          <div className="meal-tabs">
            {meals.map((meal) => (
              <button
                key={meal}
                type="button"
                className={
                  selectedMeal === meal ? 'meal-tab active' : 'meal-tab'
                }
                onClick={() => setSelectedMeal(meal)}
              >
                {meal[0].toUpperCase() + meal.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {loading && <p>Loading menu...</p>}
        {error && <p role="alert">Could not load menu: {error}</p>}

        {menu && (
          <div className="dish-list">
            {menu.dishes.map((dish, index) => (
              <article className="dish-card" key={dish.id}>
                <div className="dish-number">
                  {String(index + 1).padStart(2, '0')}
                </div>

                <div className="dish-info">
                  <h3>{dish.name}</h3>
                  <p>
                    {dish.rating_count === 0
                      ? 'No ratings yet'
                      : `${dish.rating_count} ${dish.rating_count === 1 ? 'rating' : 'ratings'
                      }`}
                  </p>
                </div>

                <span className="rating">
                  ☆{' '}
                  <span>
                    {dish.average_rating === null
                      ? '—'
                      : dish.average_rating.toFixed(1)}
                  </span>
                </span>

                <div className="rating-controls">
                  <span>Rate:</span>

                  {[1, 2, 3, 4, 5].map((score) => (
                    <button
                      key={score}
                      type="button"
                      className={
                        selectedRatings[dish.id] === score
                          ? 'score-button selected'
                          : 'score-button'
                      }
                      aria-pressed={selectedRatings[dish.id] === score}
                      onClick={() =>
                        setSelectedRatings((previous) => ({
                          ...previous,
                          [dish.id]: score,
                        }))
                      }
                    >
                      {score}
                    </button>
                  ))}

                  <button
                    type="button"
                    className="submit-rating"
                    disabled={
                      !selectedRatings[dish.id] || !accessToken
                    }
                    onClick={() => handleRatingSubmit(dish.id)}
                  >
                    Submit
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  )
}

export default App
