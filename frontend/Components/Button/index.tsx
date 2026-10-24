
// Import index.css dependencies.
import './index.css'
// Define the Button handler/helper.
const Button = ({ name, onClickFunction, isSecondaryButton }: { name: string, onClickFunction: () => void, isSecondaryButton?: boolean }) => {

  // Return the current operation's result.
  return (
    // Render button and handle onClick.
    <button className={isSecondaryButton ? "button-secondary" : "button-primary"} onClick={onClickFunction}>
      {name}
    </button>
  )
}

// Export this module's public entry point.
export default Button

/* File summary
 * - Renders a shared primary/secondary button.
 * - Invokes the callback supplied by its parent.
 */
