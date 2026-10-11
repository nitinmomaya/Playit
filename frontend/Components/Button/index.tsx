
import './index.css'
const Button = ({ name, onClickFunction, isSecondaryButton }: { name: string, onClickFunction: () => void, isSecondaryButton?: boolean }) => {

  return (
    <button className={isSecondaryButton ? "button-secondary" : "button-primary"} onClick={onClickFunction}>
      {name}
    </button>
  )
}

export default Button