import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type UserRating = {
  id: number
  dish_id: number
  mess_id: number
  score: number
  created_at: string
}

type Dish = {
  id: number
  name: string
  average_rating: number | null
  rating_count: number
}

type MenuResponse = {
  mess_id?: number
  weekday: number
  meal_type: string
  dishes: Dish[]
}

type Meal = 'breakfast' | 'lunch' | 'dinner'

type LoginResponse = {
  access_token: string
  token_type: string
}

type Mess = {
  id: number
  name: string
  is_active: boolean
}

type RushSummary = {
  mess_id: number
  meal_type: Meal
  slot_start: string
  current_rush: 'low' | 'moderate' | 'high' | 'mixed' | 'no_data_yet'
  current_reports: number
  predicted_rush:
  | 'low'
  | 'moderate'
  | 'high'
  | 'mixed'
  | 'not_enough_historical_data'
  historical_reports: number
}

type RushLevel = 'low' | 'moderate' | 'high'

const meals: Meal[] = ['breakfast', 'lunch', 'dinner']
const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

const mealWindows: Record<Meal, { start: number; end: number }> = {
  breakfast: { start: 7 * 60 + 30, end: 10 * 60 },
  lunch: { start: 12 * 60 + 30, end: 14 * 60 + 30 },
  dinner: { start: 20 * 60, end: 22 * 60 },
}

function isMealActive(meal: Meal, now = new Date()) {
  const minuteOfDay = now.getHours() * 60 + now.getMinutes()
  const window = mealWindows[meal]
  return minuteOfDay >= window.start && minuteOfDay < window.end
}

function rushLabel(level: string) {
  const labels: Record<string, string> = {
    low: 'Low',
    moderate: 'Moderate',
    high: 'High',
    mixed: 'Mixed',
    no_data_yet: 'No data yet',
    not_enough_historical_data: 'Not enough historical data',
  }
  return labels[level] ?? level
}

function App() {
  const [menu, setMenu] = useState<MenuResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedMeal, setSelectedMeal] = useState<Meal>('breakfast')
  const [messes, setMesses] = useState<Mess[]>([])
  const [messId, setMessId] = useState<number | null>(null)
  const [rushSummary, setRushSummary] = useState<RushSummary | null>(null)
  const [rushLoading, setRushLoading] = useState(false)
  const [rushError, setRushError] = useState<string | null>(null)
  const [rushMessage, setRushMessage] = useState('')
  const [rushSubmitting, setRushSubmitting] = useState(false)
  const [selectedRushLevel, setSelectedRushLevel] = useState<RushLevel | null>(null)
  const [rushRefresh, setRushRefresh] = useState(0)

  const [selectedRatings, setSelectedRatings] = useState<
    Record<number, number>
  >({})

  const [myRatings, setMyRatings] = useState<Record<number, number>>({})

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
    async function validateSession() {
      if (!accessToken) return

      try {
        const response = await fetch(`${API_URL}/auth/me`, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        })

        if (response.status === 401) {
          localStorage.removeItem('access_token')
          setAccessToken(null)
          setMyRatings({})
          setSelectedRatings({})
        }
      } catch (err) {
        console.error('Failed to validate session:', err)
      }
    }

    validateSession()
  }, [accessToken])

  useEffect(() => {
    async function fetchMesses() {
      try {
        const response = await fetch(`${API_URL}/messes`)
        if (!response.ok) throw new Error('Could not load messes.')
        const data: Mess[] = await response.json()
        const activeMesses = data.filter((mess) => mess.is_active)
        setMesses(activeMesses)
        if (activeMesses.length > 0) {
          setMessId((current) => current ?? activeMesses[0].id)
        }
      } catch (err) {
        console.error('Failed to load messes:', err)
      }
    }

    fetchMesses()
  }, [])

  useEffect(() => {
    // Refresh periodically so the displayed slot follows the server's 15-minute windows.
    const intervalId = window.setInterval(() => setRushRefresh((value) => value + 1), 30000)
    return () => window.clearInterval(intervalId)
  }, [])

  useEffect(() => {
    async function fetchRushSummary() {
      if (messId === null || !isMealActive(selectedMeal)) {
        setRushSummary(null)
        setRushError(null)
        setRushLoading(false)
        return
      }

      try {
        setRushLoading(true)
        setRushError(null)
        const response = await fetch(
          `${API_URL}/rush/summary/${messId}/${selectedMeal}`,
        )
        const data = await response.json().catch(() => null)
        if (!response.ok) {
          throw new Error(data?.detail ?? 'Could not load rush summary.')
        }
        setRushSummary(data as RushSummary)
      } catch (err) {
        setRushError(err instanceof Error ? err.message : 'Could not load rush summary.')
      } finally {
        setRushLoading(false)
      }
    }

    fetchRushSummary()
  }, [messId, selectedMeal, rushRefresh])

  function handleMealChange(meal: Meal) {
    setSelectedMeal(meal)
    setSelectedRushLevel(null)
    setRushMessage('')
  }

  function handleMessChange(newMessId: number) {
    if (messId !== newMessId) {
      setMessId(newMessId)
      setMyRatings({})
      setSelectedRatings({})
    }
  }

  async function handleRushSubmit() {
    if (!messId || !selectedRushLevel) return
    if (!accessToken) {
      setRushMessage('Please log in before submitting a rush report.')
      return
    }
    if (!isMealActive(selectedMeal)) {
      setRushMessage('Rush reports are only accepted during serving hours.')
      return
    }

    setRushSubmitting(true)
    setRushMessage('')
    try {
      const response = await fetch(`${API_URL}/rush/reports`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          mess_id: messId,
          meal_type: selectedMeal,
          level: selectedRushLevel,
        }),
      })
      const data = await response.json().catch(() => null)
      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('access_token')
          setAccessToken(null)
        }
        throw new Error(data?.detail ?? `Rush report failed: ${response.status}`)
      }

      setRushMessage('Rush report submitted.')
      setSelectedRushLevel(null)
      setRushRefresh((value) => value + 1)
    } catch (err) {
      setRushMessage(err instanceof Error ? err.message : 'Could not submit rush report.')
    } finally {
      setRushSubmitting(false)
    }
  }

  useEffect(() => {
    async function fetchMenu() {
      if (messId === null) return

      try {
        setLoading(true)
        setError(null)

        const response = await fetch(
          `${API_URL}/menus/today/${selectedMeal}?mess_id=${messId}`,
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
  }, [selectedMeal, messId])

  useEffect(() => {
    async function fetchMyRatings() {
      if (!accessToken || messId === null) {
        setMyRatings({})
        setSelectedRatings({})
        return
      }

      try {
        const response = await fetch(`${API_URL}/ratings/me?mess_id=${messId}`, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        })

        if (!response.ok) {
          throw new Error('Could not load your ratings.')
        }

        const ratings: UserRating[] = await response.json()
        const ratingsMap: Record<number, number> = {}

        for (const rating of ratings) {
          ratingsMap[rating.dish_id] = rating.score
        }

        setMyRatings(ratingsMap)

        setSelectedRatings(ratingsMap)
      } catch (err) {
        console.error('Failed to fetch your ratings:', err)
      }
    }

    fetchMyRatings()
  }, [accessToken, messId])

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
    setMyRatings({})
    setSelectedRatings({})
  }

  async function handleRatingSubmit(dishId: number) {
    const score = selectedRatings[dishId]

    if (!score || messId === null) return

    if (!accessToken) {
      setAuthMessage('Please log in before submitting a rating.')
      return
    }

    setAuthMessage('')

    try {
      const isUpdating = myRatings[dishId] !== undefined

      const response = await fetch(
        isUpdating
          ? `${API_URL}/ratings/${dishId}`
          : `${API_URL}/ratings`,
        {
          method: isUpdating ? 'PUT' : 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify(
            isUpdating
              ? { score, mess_id: messId }
              : { dish_id: dishId, score, mess_id: messId },
          ),
        },
      )

      // Handle errors before updating local rating state.
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

      // Only update local state after the server confirms success.
      setMyRatings((previous) => ({
        ...previous,
        [dishId]: score,
      }))

      setAuthMessage('Rating submitted successfully.')

      // Refresh the menu so updated averages and counts appear.
      const menuResponse = await fetch(
        `${API_URL}/menus/today/${selectedMeal}?mess_id=${messId}`,
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

  const currentMessName = messes.find((m) => m.id === messId)?.name.toUpperCase() ?? 'CAMPUS MESS'

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
                {authMode === 'login'
                  ? 'Welcome back'
                  : 'Create your account'}
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
                className={
                  authMode === 'login' ? 'auth-tab active' : 'auth-tab'
                }
                onClick={() => {
                  setAuthMode('login')
                  setAuthMessage('')
                }}
              >
                Login
              </button>

              <button
                type="button"
                className={
                  authMode === 'register' ? 'auth-tab active' : 'auth-tab'
                }
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
            <p className="eyebrow">NIT PATNA · {currentMessName}</p>
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
                onClick={() => handleMealChange(meal)}
              >
                {meal[0].toUpperCase() + meal.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {messes.length > 0 && (
          <div className="mess-tabs" role="tablist" aria-label="Select mess">
            {messes.map((mess) => (
              <button
                key={mess.id}
                type="button"
                role="tab"
                aria-selected={messId === mess.id}
                className={messId === mess.id ? 'mess-tab active' : 'mess-tab'}
                onClick={() => handleMessChange(mess.id)}
              >
                {mess.name}
              </button>
            ))}
          </div>
        )}

        <section className="rush-panel" aria-labelledby="rush-heading">
          <div className="rush-panel-heading">
            <div>
              <p className="eyebrow">LIVE MESS UPDATE</p>
              <h3 id="rush-heading">Mess Rush</h3>
              <p className="meal-serving-time">
                {selectedMeal === 'breakfast' && '7:30 AM – 10:00 AM'}
                {selectedMeal === 'lunch' && '12:30 PM – 2:30 PM'}
                {selectedMeal === 'dinner' && '8:00 PM – 10:00 PM'}
              </p>
            </div>
            <span className="rush-slot">
              {isMealActive(selectedMeal)
                ? 'Current 15-minute slot'
                : 'Outside serving hours'}
            </span>
          </div>

          {!isMealActive(selectedMeal) ? (
            <p className="rush-hint">
              Rush reports and summaries are available during this meal's serving hours.
            </p>
          ) : (
            <>
              {rushLoading && <p className="rush-hint">Loading rush data...</p>}
              {rushError && <p className="rush-error" role="alert">{rushError}</p>}
              {!rushLoading && !rushError && rushSummary && (
                <div className="rush-indicators">
                  <div className="rush-indicator">
                    <span className="rush-label">Current rush</span>
                    <strong className={`rush-value rush-${rushSummary.current_rush}`}>
                      {rushLabel(rushSummary.current_rush)}
                    </strong>
                    <span className="rush-detail">
                      {rushSummary.current_reports} {rushSummary.current_reports === 1 ? 'report' : 'reports'} this slot
                    </span>
                  </div>
                  <div className="rush-indicator">
                    <span className="rush-label">Predicted rush</span>
                    <strong className={`rush-value rush-${rushSummary.predicted_rush}`}>
                      {rushLabel(rushSummary.predicted_rush)}
                    </strong>
                    <span className="rush-detail">
                      {rushSummary.historical_reports} historical {rushSummary.historical_reports === 1 ? 'report' : 'reports'}
                    </span>
                  </div>
                </div>
              )}

              <div className="rush-report-form">
                <p className="rush-prompt">How busy is the mess right now?</p>
                <div className="rush-level-buttons">
                  {(['low', 'moderate', 'high'] as RushLevel[]).map((level) => (
                    <button
                      key={level}
                      type="button"
                      className={`rush-level-button rush-choice-${level}${selectedRushLevel === level ? ' selected' : ''}`}
                      aria-pressed={selectedRushLevel === level}
                      onClick={() => setSelectedRushLevel(level)}
                      disabled={!accessToken || rushSubmitting}
                    >
                      {rushLabel(level)}
                    </button>
                  ))}
                  <button
                    type="button"
                    className="rush-submit"
                    onClick={handleRushSubmit}
                    disabled={!accessToken || !selectedRushLevel || rushSubmitting || !messId}
                  >
                    {rushSubmitting ? 'Submitting...' : 'Report rush'}
                  </button>
                </div>
                {!accessToken && (
                  <p className="rush-hint">Log in to submit a rush report.</p>
                )}
                {rushMessage && <p className="rush-message" role="status">{rushMessage}</p>}
              </div>
            </>
          )}
        </section>

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
                    disabled={!selectedRatings[dish.id] || !accessToken}
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
