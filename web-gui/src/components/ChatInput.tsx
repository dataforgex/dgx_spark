import { useState, useRef } from 'react';
import type { KeyboardEvent, ChangeEvent } from 'react';
import './ChatInput.css';

interface ChatInputProps {
  onSend: (message: string, image?: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    const trimmed = input.trim();
    if ((trimmed || selectedImage) && !disabled) {
      onSend(trimmed, selectedImage || undefined);
      setInput('');
      setSelectedImage(null);
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setSelectedImage(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const clearImage = () => {
    setSelectedImage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="chat-input-container">
      {selectedImage && (
        <div className="image-preview">
          <img src={selectedImage} alt="Upload preview" />
          <button className="remove-image" onClick={clearImage}>×</button>
        </div>
      )}
      <div className="input-row">
        <button
          className="attach-button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          title="Attach image"
        >
          📎
        </button>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          accept="image/*"
          style={{ display: 'none' }}
        />
        <textarea
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={disabled ? "Waiting for response..." : "Type your message..."}
          disabled={disabled}
          rows={1}
        />
        <button
          className="send-button"
          onClick={handleSend}
          disabled={disabled || (!input.trim() && !selectedImage)}
        >
          Send 📤
        </button>
      </div>
    </div>
  );
}
