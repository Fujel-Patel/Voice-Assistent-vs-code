import React from 'react'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, errorMessage: '' }
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      errorMessage: error?.message || 'Unknown render error',
    }
  }

  componentDidCatch(error, errorInfo) {
    // Keep crash details visible in dev logs without crashing the whole app shell.
    console.error('UI render error:', error, errorInfo)
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className='app-error-boundary' role='alert'>
          <h2>Jarvis UI encountered an error</h2>
          <p>{this.state.errorMessage}</p>
          <button type='button' onClick={this.handleReload}>
            Reload Interface
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
