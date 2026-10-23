import React from "react";
import Broken from "../pages/Broken.jsx";

/* Catches a render error below it and shows the crash page instead of a blank screen.
   `resetKey` (the route) clears the error when the visitor navigates somewhere else; `bare` is the outer boundary
   around the whole app, which cannot rely on the nav, the planet or the page transition still working. */
export default class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(error, info) { console.error("page crashed", error, info && info.componentStack); }
  componentDidUpdate(prev) { if (this.state.error && prev.resetKey !== this.props.resetKey) this.setState({ error: null }); }
  render() {
    if (this.state.error) return <Broken error={this.state.error} bare={this.props.bare} />;
    return this.props.children;
  }
}
