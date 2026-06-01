import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center p-8">
          <div className="card-flat p-8 max-w-md w-full text-center">
            <div className="mono-label mb-2">Something went wrong</div>
            <h2 className="text-xl font-semibold mb-2" style={{ fontFamily: "Cabinet Grotesk" }}>
              Page failed to load
            </h2>
            <p className="text-sm mb-6" style={{ color: "var(--text-secondary)" }}>
              {this.state.error?.message || "An unexpected error occurred."}
            </p>
            <button
              className="btn-primary"
              onClick={() => { this.setState({ error: null }); window.location.href = "/dashboard"; }}
            >
              Go to Dashboard
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}