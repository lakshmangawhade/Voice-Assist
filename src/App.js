import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Send } from 'lucide-react';
import './App.css';

const DentalVoiceAI = () => {
  const [isListening, setIsListening] = useState(false);
  const [isWakeWordMode, setIsWakeWordMode] = useState(true);
  const [transcript, setTranscript] = useState('');
  const [conversationLog, setConversationLog] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [userInteracted, setUserInteracted] = useState(false);
  const chatEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const wakeWordRecognitionRef = useRef(null);
  const inputRef = useRef(null);
  const isWakeWordModeRef = useRef(true);
  const isListeningRef = useRef(false);
  const wakeWordActiveRef = useRef(false);
  const commandActiveRef = useRef(false);
  const silenceTimeoutRef = useRef(null);
  const wakeWordRestartTimeoutRef = useRef(null);
  const audioRef = useRef(null);
  const audioContextRef = useRef(null);
  const hasShownWakeWordMessageRef = useRef(false);
  const WAKE_WORD = 'krish';
  const SILENCE_TIMEOUT = 5000;

  const addToLog = (speaker, message, type = 'normal') => {
    setConversationLog(prev => [...prev, { 
      speaker, 
      message, 
      type, 
      timestamp: new Date().toLocaleTimeString() 
    }]);
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversationLog]);

  // Check API keys on mount
  useEffect(() => {
    const groqApiKey = process.env.REACT_APP_GROQ_API_KEY;
    const deepgramApiKey = process.env.REACT_APP_DEEPGRAM_API_KEY;
    
    if (!groqApiKey || groqApiKey === 'your_groq_api_key_here' || groqApiKey.trim() === '') {
      addToLog('System', '⚠️ Groq API Key not configured. Please add REACT_APP_GROQ_API_KEY to your .env file and restart the server.', 'system');
    } else {
      console.log('✅ Groq API Key configured successfully');
    }
    
    if (!deepgramApiKey || deepgramApiKey === 'your_deepgram_api_key_here' || deepgramApiKey.trim() === '') {
      addToLog('System', '⚠️ Deepgram API Key not configured. Please add REACT_APP_DEEPGRAM_API_KEY to your .env file. Falling back to browser speech synthesis.', 'system');
    } else {
      console.log('✅ Deepgram API Key configured successfully');
      console.log('✅ Deepgram TTS will be used for voice output');
    }
  }, []);

  // Enable user interaction for audio autoplay
  useEffect(() => {
    const enableAudio = () => {
      if (!userInteracted) {
        setUserInteracted(true);
        console.log('✅ User interaction detected - audio autoplay enabled');
      }
    };

    // Listen for any user interaction
    document.addEventListener('click', enableAudio, { once: true });
    document.addEventListener('keydown', enableAudio, { once: true });
    document.addEventListener('touchstart', enableAudio, { once: true });

    return () => {
      document.removeEventListener('click', enableAudio);
      document.removeEventListener('keydown', enableAudio);
      document.removeEventListener('touchstart', enableAudio);
    };
  }, [userInteracted]);

  // Initialize audio context on first user interaction
  useEffect(() => {
    const handleInteraction = () => {
      if (!userInteracted) {
        console.log('✅ User interaction detected - audio enabled');
        setUserInteracted(true);
        
        // Initialize audio context
        if (!audioContextRef.current) {
          try {
            audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
            console.log('✅ Audio context initialized');
          } catch (error) {
            console.error('Error initializing audio context:', error);
          }
        }
      }
    };

    // Listen for any user interaction
    document.addEventListener('click', handleInteraction, { once: false });
    document.addEventListener('keydown', handleInteraction, { once: false });
    document.addEventListener('touchstart', handleInteraction, { once: false });

    return () => {
      document.removeEventListener('click', handleInteraction);
      document.removeEventListener('keydown', handleInteraction);
      document.removeEventListener('touchstart', handleInteraction);
    };
  }, [userInteracted]);

  // Sync refs with state
  useEffect(() => {
    isWakeWordModeRef.current = isWakeWordMode;
  }, [isWakeWordMode]);

  useEffect(() => {
    isListeningRef.current = isListening;
  }, [isListening]);

  const clearSilenceTimeout = () => {
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }
  };

  const startSilenceTimer = () => {
    clearSilenceTimeout();
    
    silenceTimeoutRef.current = setTimeout(() => {
      console.log('5 seconds of silence - returning to wake word mode');
      stopCommandRecognition();
      setIsWakeWordMode(true);
      setTimeout(() => startWakeWordDetection(), 300);
      addToLog('System', 'Returning to wake word mode. Say "krish" to continue.', 'system');
    }, SILENCE_TIMEOUT);
  };

  const stopWakeWordDetection = () => {
    if (wakeWordRecognitionRef.current && wakeWordActiveRef.current) {
      try {
        wakeWordRecognitionRef.current.stop();
        wakeWordActiveRef.current = false;
        console.log('Wake word detection stopped');
      } catch (e) {
        console.log('Error stopping wake word detection:', e.message);
      }
    }
    
    if (wakeWordRestartTimeoutRef.current) {
      clearTimeout(wakeWordRestartTimeoutRef.current);
      wakeWordRestartTimeoutRef.current = null;
    }
  };

  const stopCommandRecognition = () => {
    if (recognitionRef.current && commandActiveRef.current) {
      try {
        recognitionRef.current.stop();
        commandActiveRef.current = false;
        setIsListening(false);
        console.log('Command recognition stopped');
      } catch (e) {
        console.log('Error stopping command recognition:', e.message);
      }
    }
    clearSilenceTimeout();
  };

  const startWakeWordDetection = () => {
    if (!wakeWordRecognitionRef.current || !isWakeWordModeRef.current || wakeWordActiveRef.current) {
      return;
    }

    stopCommandRecognition();
    
    try {
      wakeWordRecognitionRef.current.start();
      wakeWordActiveRef.current = true;
      console.log('✅ Wake word detection started - listening for "krish"');
      
      // Only show the message once when first starting
      if (!hasShownWakeWordMessageRef.current) {
        addToLog('System', `Listening for wake word "krish"...`, 'system');
        hasShownWakeWordMessageRef.current = true;
      }
    } catch (error) {
      if (error.name === 'InvalidStateError') {
        console.log('Wake word recognition already started');
      } else {
        console.error('Error starting wake word detection:', error);
        addToLog('System', 'Error starting wake word detection. Please refresh the page.', 'system');
      }
      wakeWordActiveRef.current = false;
    }
  };

  const startCommandListening = () => {
    if (!recognitionRef.current || commandActiveRef.current) {
      return;
    }

    stopWakeWordDetection();
    
    try {
      recognitionRef.current.start();
      commandActiveRef.current = true;
      setIsListening(true);
      setIsWakeWordMode(false);
      console.log('✅ Command listening started');
      addToLog('System', '🎤 Activated! Listening for your command...', 'system');
      
      startSilenceTimer();
    } catch (error) {
      if (error.name === 'InvalidStateError') {
        console.log('Command recognition already started');
      } else {
        console.error('Error starting command recognition:', error);
        commandActiveRef.current = false;
        setIsListening(false);
        setIsWakeWordMode(true);
        setTimeout(() => startWakeWordDetection(), 300);
      }
    }
  };

  useEffect(() => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      addToLog('System', 'Speech recognition is not supported in your browser. Please use text input instead.', 'system');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    // Initialize wake word recognition
    wakeWordRecognitionRef.current = new SpeechRecognition();
    wakeWordRecognitionRef.current.continuous = true;
    wakeWordRecognitionRef.current.interimResults = true;
    wakeWordRecognitionRef.current.lang = 'en-US';

    wakeWordRecognitionRef.current.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript.toLowerCase().trim();
        
        if (event.results[i].isFinal) {
          console.log('Wake word mode heard:', transcript);
        }
        
        const words = transcript.split(/\s+/);
        const hasWakeWord = words.includes(WAKE_WORD) || 
                           transcript.includes(WAKE_WORD) ||
                           words.some(word => word.includes(WAKE_WORD));
        
        if (hasWakeWord && isWakeWordModeRef.current) {
          console.log('🎯 WAKE WORD DETECTED:', transcript);
          wakeWordActiveRef.current = false;
          
          try {
            wakeWordRecognitionRef.current.stop();
          } catch (e) {
            console.log('Error stopping wake word recognition:', e.message);
          }
          
          setTimeout(() => {
            startCommandListening();
          }, 300);
          break;
        }
      }
    };

    wakeWordRecognitionRef.current.onerror = (event) => {
      if (event.error !== 'no-speech' && event.error !== 'aborted') {
        console.error('Wake word recognition error:', event.error);
        
        if (event.error === 'not-allowed') {
          addToLog('System', 'Microphone access denied. Please allow microphone access in your browser settings.', 'system');
        }
      }
      wakeWordActiveRef.current = false;
    };

    wakeWordRecognitionRef.current.onend = () => {
      wakeWordActiveRef.current = false;
      
      if (isWakeWordModeRef.current) {
        wakeWordRestartTimeoutRef.current = setTimeout(() => {
          if (isWakeWordModeRef.current && !wakeWordActiveRef.current) {
            startWakeWordDetection();
          }
        }, 500);
      }
    };

    // Initialize command recognition
    recognitionRef.current = new SpeechRecognition();
    recognitionRef.current.continuous = true;
    recognitionRef.current.interimResults = true;
    recognitionRef.current.lang = 'en-US';

    recognitionRef.current.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
        } else {
          interimTranscript += transcript;
        }
      }

      if (interimTranscript) {
        setTranscript(interimTranscript);
        clearSilenceTimeout();
      }

      if (finalTranscript) {
        const trimmedTranscript = finalTranscript.trim();
        
        if (trimmedTranscript.length > 0) {
          console.log('Final transcript:', trimmedTranscript);
          setTranscript(trimmedTranscript);
          clearSilenceTimeout();
          handleUserMessage(trimmedTranscript);
        }
      }
    };

    recognitionRef.current.onerror = (event) => {
      console.error('Command recognition error:', event.error);
      
      if (event.error === 'no-speech') {
        console.log('No speech detected, continuing to listen...');
      } else if (event.error === 'not-allowed') {
        addToLog('System', 'Microphone access denied. Please allow microphone access in your browser settings.', 'system');
        commandActiveRef.current = false;
        setIsListening(false);
        setIsWakeWordMode(true);
      } else {
        commandActiveRef.current = false;
        setIsListening(false);
        setIsWakeWordMode(true);
        setTimeout(() => startWakeWordDetection(), 500);
      }
    };

    recognitionRef.current.onend = () => {
      commandActiveRef.current = false;
      
      if (!isWakeWordModeRef.current && isListeningRef.current) {
        console.log('Command recognition ended unexpectedly, restarting...');
        setTimeout(() => {
          if (!isWakeWordModeRef.current) {
            startCommandListening();
          }
        }, 100);
      } else {
        setIsListening(false);
      }
    };

    const initTimeout = setTimeout(() => {
      startWakeWordDetection();
    }, 500);

    return () => {
      clearTimeout(initTimeout);
      clearSilenceTimeout();
      if (wakeWordRestartTimeoutRef.current) {
        clearTimeout(wakeWordRestartTimeoutRef.current);
      }
      
      stopWakeWordDetection();
      stopCommandRecognition();
      
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
    };
  }, []);

  const callGroqAPI = async (userMessage, currentConversationLog) => {
    const apiKey = process.env.REACT_APP_GROQ_API_KEY;
    
    if (!apiKey || apiKey === 'your_groq_api_key_here' || apiKey.trim() === '') {
      const errorMsg = 'Groq API key is not configured. Please:\n1. Create a .env file in the root directory\n2. Add: REACT_APP_GROQ_API_KEY=your_actual_api_key\n3. Restart the development server (npm start)';
      console.error(errorMsg);
      throw new Error(errorMsg);
    }

    const conversationHistory = currentConversationLog
      .filter(log => log.type === 'user' || log.type === 'ai')
      .map(log => ({
        role: log.type === 'user' ? 'user' : 'assistant',
        content: log.message
      }));

    try {
      const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'llama-3.1-8b-instant',
          messages: [
            {
              role: 'system',
              content: 'You are a helpful dental practice AI assistant named Krish. You help with appointments, patient information, scheduling, and general dental practice questions. Keep your responses concise and conversational, ideally under 3 sentences unless more detail is specifically requested. Be professional and friendly.'
            },
            ...conversationHistory,
            {
              role: 'user',
              content: userMessage
            }
          ],
          temperature: 0.7,
          max_tokens: 1024,
          top_p: 1,
          stream: false
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error?.message || `API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return data.choices[0]?.message?.content || 'I apologize, but I could not generate a response.';
    } catch (error) {
      console.error('Groq API error:', error);
      throw error;
    }
  };

  const speakWithDeepgram = async (text) => {
    const apiKey = process.env.REACT_APP_DEEPGRAM_API_KEY;
    
    if (!apiKey || apiKey === 'your_deepgram_api_key_here' || apiKey.trim() === '') {
      console.warn('⚠️ Deepgram API key not configured, falling back to browser speech synthesis');
      addToLog('System', '⚠️ Deepgram TTS not configured. Using browser voice.', 'system');
      return speakWithBrowserTTS(text);
    }

    // Ensure user has interacted for audio autoplay (required by browsers)
    if (!userInteracted) {
      console.warn('⚠️ User has not interacted yet. Audio autoplay may be blocked by browser.');
      console.log('Attempting to enable user interaction...');
      setUserInteracted(true);
      // Still try to play - some browsers allow it after setting the flag
    }

    try {
      setIsSpeaking(true);
      console.log('🎙️ Generating speech with Deepgram TTS...');
      console.log('Text to speak:', text.substring(0, 50) + '...');

      // Deepgram TTS API endpoint with voice model
      const response = await fetch('https://api.deepgram.com/v1/speak?model=aura-asteria-en', {
        method: 'POST',
        headers: {
          'Authorization': `Token ${apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: text
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Deepgram TTS API error:', response.status, response.statusText, errorText);
        throw new Error(`Deepgram TTS API error: ${response.status} ${response.statusText}`);
      }

      console.log('✅ Deepgram TTS response received');
      const audioBlob = await response.blob();
      console.log('Audio blob size:', audioBlob.size, 'bytes');
      
      if (audioBlob.size === 0) {
        throw new Error('Empty audio blob received from Deepgram');
      }

      const audioUrl = URL.createObjectURL(audioBlob);
      
      // Stop any existing audio
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
        audioRef.current = null;
      }
      
      const audio = new Audio(audioUrl);
      audioRef.current = audio;
      
      // Set volume and ensure it's ready
      audio.volume = 1.0;
      audio.preload = 'auto';
      
      return new Promise((resolve, reject) => {
        // Wait for audio to be ready
        audio.addEventListener('canplaythrough', () => {
          console.log('✅ Audio ready to play');
        }, { once: true });

        audio.onended = () => {
          console.log('✅ Deepgram speech completed successfully');
          setIsSpeaking(false);
          URL.revokeObjectURL(audioUrl);
          audioRef.current = null;
          
          if (!isWakeWordModeRef.current) {
            startSilenceTimer();
          }
          resolve();
        };

        audio.onerror = (error) => {
          console.error('❌ Audio playback error:', error);
          setIsSpeaking(false);
          URL.revokeObjectURL(audioUrl);
          audioRef.current = null;
          
          console.log('Falling back to browser TTS due to playback error');
          speakWithBrowserTTS(text).then(resolve).catch(reject);
        };

        // Play audio with proper error handling
        const playPromise = audio.play();
        
        if (playPromise !== undefined) {
          playPromise
            .then(() => {
              console.log('✅ Deepgram audio playback started successfully');
            })
            .catch(error => {
              console.error('❌ Error playing Deepgram audio:', error);
              setIsSpeaking(false);
              URL.revokeObjectURL(audioUrl);
              audioRef.current = null;
              
              console.log('Falling back to browser TTS due to play() error');
              speakWithBrowserTTS(text).then(resolve).catch(reject);
            });
        } else {
          // If play() returns undefined, try to play anyway
          audio.play().catch(error => {
            console.error('Error playing audio:', error);
            speakWithBrowserTTS(text).then(resolve).catch(reject);
          });
        }
      });

    } catch (error) {
      console.error('❌ Deepgram TTS error:', error);
      setIsSpeaking(false);
      addToLog('System', `Deepgram TTS error: ${error.message}. Using browser voice.`, 'system');
      return speakWithBrowserTTS(text);
    }
  };

  const speakWithBrowserTTS = (text) => {
    return new Promise((resolve) => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;
        
        utterance.onend = () => {
          console.log('✅ Browser speech synthesis completed');
          setIsSpeaking(false);
          
          if (!isWakeWordModeRef.current) {
            startSilenceTimer();
          }
          resolve();
        };
        
        utterance.onerror = (error) => {
          console.error('Speech synthesis error:', error);
          setIsSpeaking(false);
          
          if (!isWakeWordModeRef.current) {
            startSilenceTimer();
          }
          resolve();
        };
        
        setIsSpeaking(true);
        window.speechSynthesis.speak(utterance);
      } else {
        if (!isWakeWordModeRef.current) {
          startSilenceTimer();
        }
        resolve();
      }
    });
  };

  const handleUserMessage = async (message) => {
    if (!message || message.trim() === '') return;

    // Mark user as interacted (for audio autoplay)
    if (!userInteracted) {
      setUserInteracted(true);
    }

    clearSilenceTimeout();

    addToLog('You', message, 'user');
    setTranscript('');
    setInputMessage('');
    setIsLoading(true);

    try {
      const currentLog = [...conversationLog, { 
        speaker: 'You', 
        message, 
        type: 'user', 
        timestamp: new Date().toLocaleTimeString() 
      }];
      
      const aiResponse = await callGroqAPI(message, currentLog);
      addToLog('Krish', aiResponse, 'ai');
      
      setIsLoading(false);
      
      await speakWithDeepgram(aiResponse);
      
    } catch (error) {
      const errorMessage = error.message || 'Failed to get response from AI. Please try again.';
      addToLog('System', `Error: ${errorMessage}`, 'system');
      console.error('Error handling user message:', error);
      setIsLoading(false);
      
      if (!isWakeWordModeRef.current) {
        startSilenceTimer();
      }
    }
  };

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (inputMessage.trim() && !isLoading) {
      handleUserMessage(inputMessage.trim());
    }
  };

  const toggleListening = () => {
    if (!recognitionRef.current) {
      addToLog('System', 'Speech recognition is not available in your browser.', 'system');
      return;
    }

    // Mark user as interacted
    if (!userInteracted) {
      setUserInteracted(true);
    }

    if (isListening) {
      stopCommandRecognition();
      setIsWakeWordMode(true);
      setTimeout(() => startWakeWordDetection(), 300);
    } else {
      stopWakeWordDetection();
      setIsWakeWordMode(false);
      startCommandListening();
    }
  };

  return (
    <div className="app-container">
      <div className="chat-container">
        <div className="chat-header">
          <h1>Dental AI Assistant - Krish</h1>
          <div className="status-indicator">
            <div className={`status-dot ${isListening ? 'listening' : isWakeWordMode ? 'wake-word' : 'ready'}`}></div>
            <span>
              {isSpeaking ? '🔊 Speaking' : isListening ? 'Listening' : isWakeWordMode ? 'Waiting for "krish"' : 'Ready'}
            </span>
          </div>
        </div>

        <div className="chat-messages">
          {conversationLog.length === 0 && (
            <div className="empty-state">
              <Mic className="empty-icon" />
              <p className="empty-title">Say "krish" to activate</p>
              <p className="empty-subtitle">Or type a message below to start chatting</p>
            </div>
          )}
          
          {conversationLog.map((log, index) => (
            <div key={index} className={`message-wrapper ${log.type}`}>
              <div className={`message ${log.type}`}>
                <div className="message-header">
                  <span className="message-speaker">{log.speaker}</span>
                  <span className="message-time">{log.timestamp}</span>
                </div>
                <div className="message-content">{log.message}</div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="message-wrapper ai">
              <div className="message ai">
                <div className="message-content">
                  <span className="typing-indicator">Krish is thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="chat-input-area">
          {transcript && (
            <div className="transcript-preview">
              <span className="transcript-label">You said:</span>
              <span className="transcript-text">"{transcript}"</span>
            </div>
          )}
          
          <form onSubmit={handleSendMessage} className="input-form">
            <input
              ref={inputRef}
              type="text"
              className="text-input"
              placeholder={isListening ? 'Listening...' : isWakeWordMode ? 'Say "krish" or type a message...' : 'Type your message here...'}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              disabled={isListening || isLoading}
            />
            
            <div className="input-buttons">
              <button
                type="button"
                onClick={toggleListening}
                className={`mic-button ${isListening ? 'listening' : ''} ${isWakeWordMode ? 'wake-word-active' : ''}`}
                title={isListening ? 'Stop listening' : 'Start voice input'}
                aria-label={isListening ? 'Stop listening' : 'Start voice input'}
                disabled={isLoading}
              >
                {isListening ? (
                  <MicOff className="icon" />
                ) : (
                  <Mic className="icon" />
                )}
              </button>
              
              <button
                type="submit"
                className="send-button"
                disabled={(!inputMessage.trim() && !isListening) || isLoading}
                title="Send message"
                aria-label="Send message"
              >
                <Send className="icon" />
              </button>
            </div>
          </form>
          
          {isWakeWordMode && (
            <div className="wake-word-hint">
              <span className="wake-word-text">💡 Say "{WAKE_WORD}" to activate voice commands</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DentalVoiceAI;