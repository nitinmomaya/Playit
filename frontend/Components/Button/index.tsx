
import './index.css'
const Button = ({ name, onClickFunction }: { name: string, onClickFunction: () => void }) => {
  return (
    <button className="button-primary" onClick={onClickFunction}>
      {name}
    </button>
  )
}

export default Button