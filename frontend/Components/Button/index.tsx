
import type { ReactNode } from 'react'
import './index.css'
const Button = ({ name, onClickFunction, isSecondaryButton, icon }: { name: string, onClickFunction: () => void, isSecondaryButton?: boolean, icon?: ReactNode }) => {

  return (
    <button className={isSecondaryButton ? "button-secondary" : "button-primary"} onClick={onClickFunction}>
      {icon && <span className="button-icon" aria-hidden="true">{icon}</span>}
      {name}
    </button>
  )
}

export default Button