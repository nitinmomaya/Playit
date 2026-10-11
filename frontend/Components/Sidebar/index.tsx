import React from 'react'
import Button from '../Button'
import './index.css'

const Sidebar = () => {

    const totalChatHistory=[`old songs 2000's`, 'rock classics', 'pop hits']
  return (
    <div className="sidebar-container">
        <Button
          name="New Chat"
          onClickFunction={() => console.log('Button clicked')}
          isSecondaryButton={true}
        />

        {totalChatHistory.map((chat, index) => (
          <div className="chat-history-item" key={index}>{chat}</div>
        ))}

    </div>
  )
}

export default Sidebar