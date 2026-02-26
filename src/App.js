import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Send, Sun, Moon, Phone, X } from 'lucide-react';
import './App.css';
import profilePhoto from './assets/chat/profile_photo.jpg';

// Import light theme images
import light_tooth1_1 from './assets/light/tooth1_1.png';
import light_tooth1_2 from './assets/light/tooth1_2.png';
import light_tooth1_3 from './assets/light/tooth1_3.png';
import light_tooth1_4 from './assets/light/tooth1_4.png';
import light_tooth1_5 from './assets/light/tooth1_5.png';
import light_tooth1_6 from './assets/light/tooth1_6.png';
import light_tooth2_1 from './assets/light/tooth2_1.png';
import light_tooth2_2 from './assets/light/tooth2_2.png';
import light_tooth2_3 from './assets/light/tooth2_3.png';
import light_tooth2_4 from './assets/light/tooth2_4.png';
import light_tooth2_5 from './assets/light/tooth2_5.png';
import light_tooth2_6 from './assets/light/tooth2_6.png';
import light_tooth2_7 from './assets/light/tooth2_7.png';
import light_tooth3_1 from './assets/light/tooth3_1.png';
import light_tooth3_2 from './assets/light/tooth3_2.png';
import light_tooth3_3 from './assets/light/tooth3_3.png';
import light_tooth3_4 from './assets/light/tooth3_4.png';
import light_tooth3_5 from './assets/light/tooth3_5.png';
import light_tooth3_6 from './assets/light/tooth3_6.png';
import light_tooth3_7 from './assets/light/tooth3_7.png';
import light_tooth4_1 from './assets/light/tooth4_1.png';
import light_tooth4_2 from './assets/light/tooth4_2.png';
import light_tooth4_3 from './assets/light/tooth4_3.png';
import light_tooth4_4 from './assets/light/tooth4_4.png';
import light_tooth4_5 from './assets/light/tooth4_5.png';
import light_tooth4_6 from './assets/light/tooth4_6.png';
import light_tooth4_7 from './assets/light/tooth4_7.png';

// Import dark theme images
import dark_tooth1_1 from './assets/dark/toothh1_1-modified.png';
import dark_tooth1_2 from './assets/dark/tooth1_2-modified.png';
import dark_tooth1_3 from './assets/dark/tooth1_3-modified.png';
import dark_tooth1_4 from './assets/dark/tooth1_4-modified.png';
import dark_tooth1_5 from './assets/dark/tooth1_5-modified.png';
import dark_tooth1_6 from './assets/dark/tooth1_6-modified.png';
import dark_tooth2_1 from './assets/dark/tooth2_1-modified.png';
import dark_tooth2_2 from './assets/dark/tooth2_2-modified.png';
import dark_tooth2_3 from './assets/dark/tooth2_3-modified.png';
import dark_tooth2_4 from './assets/dark/tooth2_4-modified.png';
import dark_tooth2_5 from './assets/dark/tooth2_5-modified.png';
import dark_tooth2_6 from './assets/dark/tooth2_6-modified.png';
import dark_tooth2_7 from './assets/dark/tooth2_7-modified.png';
import dark_tooth3_1 from './assets/dark/tooth3_1-modified.png';
import dark_tooth3_2 from './assets/dark/tooth3_2-modified.png';
import dark_tooth3_3 from './assets/dark/tooth3_3-modified.png';
import dark_tooth3_4 from './assets/dark/tooth3_4-modified.png';
import dark_tooth3_5 from './assets/dark/tooth3_5-modified.png';
import dark_tooth3_6 from './assets/dark/tooth3_6-modified.png';
import dark_tooth3_7 from './assets/dark/tooth3_7-modified.png';
import dark_tooth4_1 from './assets/dark/tooth4_1-modified.png';
import dark_tooth4_2 from './assets/dark/tooth4_2-modified.png';
import dark_tooth4_3 from './assets/dark/tooth4_3-modified.png';
import dark_tooth4_4 from './assets/dark/tooth4_4-modified.png';
import dark_tooth4_5 from './assets/dark/tooth4_5-modified.png';
import dark_tooth4_6 from './assets/dark/tooth4_6-modified.png';
import dark_tooth4_7 from './assets/dark/tooth4_7-modified.png';

// Array of light theme images
const lightImageSequence = [
  light_tooth1_1, light_tooth1_2, light_tooth1_3, light_tooth1_4, light_tooth1_5, light_tooth1_6,
  light_tooth2_1, light_tooth2_2, light_tooth2_3, light_tooth2_4, light_tooth2_5, light_tooth2_6, light_tooth2_7,
  light_tooth3_1, light_tooth3_2, light_tooth3_3, light_tooth3_4, light_tooth3_5, light_tooth3_6, light_tooth3_7,
  light_tooth4_1, light_tooth4_2, light_tooth4_3, light_tooth4_4, light_tooth4_5, light_tooth4_6, light_tooth4_7
];

// Array of dark theme images
const darkImageSequence = [
  dark_tooth1_1, dark_tooth1_2, dark_tooth1_3, dark_tooth1_4, dark_tooth1_5, dark_tooth1_6,
  dark_tooth2_1, dark_tooth2_2, dark_tooth2_3, dark_tooth2_4, dark_tooth2_5, dark_tooth2_6, dark_tooth2_7,
  dark_tooth3_1, dark_tooth3_2, dark_tooth3_3, dark_tooth3_4, dark_tooth3_5, dark_tooth3_6, dark_tooth3_7,
  dark_tooth4_1, dark_tooth4_2, dark_tooth4_3, dark_tooth4_4, dark_tooth4_5, dark_tooth4_6, dark_tooth4_7
];

const DentalVoiceAI = () => {
  const [isListening, setIsListening] = useState(false);
  const [isWakeWordMode, setIsWakeWordMode] = useState(true);
  const [transcript, setTranscript] = useState('');
  const [conversationLog, setConversationLog] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [userInteracted, setUserInteracted] = useState(false);
  const [showIntro, setShowIntro] = useState(true);
  const [animationPosition, setAnimationPosition] = useState('center'); // 'center' or 'background'
  const [showTimeoutPopup, setShowTimeoutPopup] = useState(false);
  const [chatActive, setChatActive] = useState(false);
  const [waitingForFirstResponse, setWaitingForFirstResponse] = useState(false);
  const [introMessages, setIntroMessages] = useState([]);
  const [showCallModal, setShowCallModal] = useState(false);
  const [callInfo, setCallInfo] = useState(null);
  const [patientPhone, setPatientPhone] = useState('');
  const [patientName, setPatientName] = useState('');
  const [isCalling, setIsCalling] = useState(false);
  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem('theme');
    return savedTheme || 'dark';
  });
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  
  // Get image sequence based on theme
  const imageSequence = theme === 'light' ? darkImageSequence : lightImageSequence;
  const chatEndRef = useRef(null);
  const imageAnimationIntervalRef = useRef(null);
  const showIntroRef = useRef(true);
  const inactivityTimeoutRef = useRef(null);
  const lastInteractionRef = useRef(Date.now());
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
  const WAKE_WORD = 'giva';
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

  // Sync showIntro ref with state
  useEffect(() => {
    showIntroRef.current = showIntro;
  }, [showIntro]);

  // 2-minute inactivity timeout popup
  useEffect(() => {
    if (!showIntro) {
      const resetInactivityTimer = () => {
        lastInteractionRef.current = Date.now();
        setShowTimeoutPopup(false);
        
        if (inactivityTimeoutRef.current) {
          clearTimeout(inactivityTimeoutRef.current);
        }
        
        inactivityTimeoutRef.current = setTimeout(() => {
          setShowTimeoutPopup(true);
        }, 120000); // 2 minutes
      };

      // Reset timer on any interaction
      const handleInteraction = () => {
        resetInactivityTimer();
      };

      resetInactivityTimer();

      window.addEventListener('click', handleInteraction);
      window.addEventListener('keydown', handleInteraction);
      window.addEventListener('touchstart', handleInteraction);

      return () => {
        window.removeEventListener('click', handleInteraction);
        window.removeEventListener('keydown', handleInteraction);
        window.removeEventListener('touchstart', handleInteraction);
        if (inactivityTimeoutRef.current) {
          clearTimeout(inactivityTimeoutRef.current);
        }
      };
    }
  }, [showIntro]);

  // Preload all images for smooth animation
  useEffect(() => {
    // Preload current theme images
    imageSequence.forEach((imageSrc) => {
      const img = new Image();
      img.src = imageSrc;
    });
    
    // Preload other theme images in background
    const otherSequence = theme === 'light' ? darkImageSequence : lightImageSequence;
    otherSequence.forEach((imageSrc) => {
      const img = new Image();
      img.src = imageSrc;
    });
  }, [theme]);
  
  // Save theme to localStorage
  useEffect(() => {
    localStorage.setItem('theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);
  
  // Set initial theme attribute
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, []);
  
  const toggleTheme = () => {
    setTheme(prevTheme => prevTheme === 'light' ? 'dark' : 'light');
  };

  // Image animation at 24fps (41.67ms per frame)
  useEffect(() => {
    const FPS = 5;
    const frameInterval = 1000 / FPS; // ~41.67ms per frame

    imageAnimationIntervalRef.current = setInterval(() => {
      setCurrentImageIndex((prevIndex) => {
        return (prevIndex + 1) % imageSequence.length;
      });
    }, frameInterval);

    return () => {
      if (imageAnimationIntervalRef.current) {
        clearInterval(imageAnimationIntervalRef.current);
        imageAnimationIntervalRef.current = null;
      }
    };
  }, []);

  // Backend API URL configuration
  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

  // Check backend connection on mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/health`);
        if (response.ok) {
          const data = await response.json();
          console.log('✅ Backend connected successfully');
          if (!data.llm_configured) {
            addToLog('System', '⚠️ Backend LLM service not configured. Please check backend .env file.', 'system');
          }
          if (!data.tts_configured) {
            addToLog('System', '⚠️ Backend TTS service not configured. Will fall back to browser speech synthesis.', 'system');
          }
        } else {
          addToLog('System', '⚠️ Backend health check failed. Please ensure the backend server is running.', 'system');
        }
      } catch (error) {
        console.error('Backend connection error:', error);
        addToLog('System', '⚠️ Cannot connect to backend. Please ensure the backend server is running on ' + BACKEND_URL, 'system');
      }
    };
    checkBackend();
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
      //console.log('5 seconds of silence - returning to wake word mode');
      stopCommandRecognition();
      setIsWakeWordMode(true);
      setTimeout(() => startWakeWordDetection(), 300);
      //addToLog('System', 'Returning to wake word mode. Say "giva" to continue.', 'system');
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
      console.log('✅ Wake word detection started - listening for "giva"');
      
      // Only show the message once when first starting
      //if (!hasShownWakeWordMessageRef.current) {
      //  addToLog('System', `Listening for wake word "giva"...`, 'system');
      //  hasShownWakeWordMessageRef.current = true;
      //}
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
      //addToLog('System', '🎤 Activated! Listening for your command...', 'system');
      
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
          
          // Hide intro and move animation to background on wake word detection
          if (showIntroRef.current) {
            setShowIntro(false);
            setTimeout(() => {
              setAnimationPosition('background');
              setChatActive(true);
            }, 100);
          }

          // Reset inactivity timer
          lastInteractionRef.current = Date.now();
          setShowTimeoutPopup(false);
          
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
    // Build conversation history for backend
    const conversationHistory = currentConversationLog
      .filter(log => log.type === 'user' || log.type === 'ai')
      .map(log => ({
        role: log.type === 'user' ? 'user' : 'assistant',
        content: log.message
      }));

    try {
      const response = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          conversation_history: conversationHistory
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Backend error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      
      // Return response even if not successful - let UI handle it
      return {
        response: data.response || data.error || 'I apologize, but I could not generate a response.',
        call_info: data.call_info || null,
        success: data.success !== false  // Default to true if not specified
      };
    } catch (error) {
      console.error('Backend API error:', error);
      // Return error response instead of throwing - allows UI to transition
      return {
        response: error.message || 'I apologize, but I encountered an error. Please try again.',
        call_info: null,
        success: false
      };
    }
  };

  const initiateCall = async () => {
    if (!patientPhone.trim()) {
      addToLog('System', 'Please enter a phone number to initiate the call.', 'system');
      return;
    }

    if (!callInfo) {
      addToLog('System', 'No call information available.', 'system');
      return;
    }

    setIsCalling(true);
    addToLog('System', `Initiating call to ${patientPhone}...`, 'system');

    try {
      const response = await fetch(`${BACKEND_URL}/api/twilio/initiate-call`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phone_number: patientPhone.trim(),
          intent: callInfo.intent,
          patient_name: patientName.trim() || null,
          appointment_date: callInfo.extracted_info?.dates_mentioned?.[0] || null
        })
      });

      const data = await response.json();

      if (data.success) {
        addToLog('System', `Call initiated successfully! Call SID: ${data.call_sid}`, 'system');
        setShowCallModal(false);
        setPatientPhone('');
        setPatientName('');
        setCallInfo(null);
      } else {
        addToLog('System', `Call failed: ${data.error}`, 'system');
      }
    } catch (error) {
      console.error('Call initiation error:', error);
      addToLog('System', `Error initiating call: ${error.message}`, 'system');
    } finally {
      setIsCalling(false);
    }
  };

  const speakWithDeepgram = async (text) => {
    // Ensure user has interacted for audio autoplay (required by browsers)
    if (!userInteracted) {
      console.warn('⚠️ User has not interacted yet. Audio autoplay may be blocked by browser.');
      console.log('Attempting to enable user interaction...');
      setUserInteracted(true);
    }

    try {
      setIsSpeaking(true);
      console.log('🎙️ Generating speech with Deepgram TTS via backend...');
      console.log('Text to speak:', text.substring(0, 50) + '...');

      // Call backend TTS endpoint
      const response = await fetch(`${BACKEND_URL}/api/tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: text
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Backend TTS error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      
      if (!data.success || !data.audio_url) {
        throw new Error(data.error || 'Failed to get audio from backend');
      }

      console.log('✅ Backend TTS response received');
      
      // Backend returns base64 data URL, use it directly
      const audioUrl = data.audio_url;
      
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
          // Only revoke if it's a blob URL, not a data URL
          if (audioUrl.startsWith('blob:')) {
            URL.revokeObjectURL(audioUrl);
          }
          audioRef.current = null;
          
          if (!isWakeWordModeRef.current) {
            startSilenceTimer();
          }
          resolve();
        };

        audio.onerror = (error) => {
          console.error('❌ Audio playback error:', error);
          setIsSpeaking(false);
          // Only revoke if it's a blob URL, not a data URL
          if (audioUrl.startsWith('blob:')) {
            URL.revokeObjectURL(audioUrl);
          }
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
              // Only revoke if it's a blob URL, not a data URL
              if (audioUrl.startsWith('blob:')) {
                URL.revokeObjectURL(audioUrl);
              }
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
      console.error('❌ Backend TTS error:', error);
      setIsSpeaking(false);
      addToLog('System', `Backend TTS error: ${error.message}. Using browser voice.`, 'system');
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

    // Reset inactivity timer
    lastInteractionRef.current = Date.now();
    setShowTimeoutPopup(false);

    const isFirstMessage = showIntro && conversationLog.length === 0;
    const userMessageLog = {
      speaker: 'You',
      message,
      type: 'user',
      timestamp: new Date().toLocaleTimeString()
    };
    
    if (isFirstMessage) {
      // Add message to intro messages
      setIntroMessages([userMessageLog]);
      setWaitingForFirstResponse(true);
    } else {
      addToLog('You', message, 'user');
    }

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
      const responseText = aiResponse.response || 'I apologize, but I could not generate a response.';
      
      if (isFirstMessage) {
        // Add AI response to intro messages
        const aiMessageLog = {
          speaker: 'Giva',
          message: responseText,
          type: 'ai',
          timestamp: new Date().toLocaleTimeString()
        };
        const updatedIntroMessages = [userMessageLog, aiMessageLog];
        
        // Update intro messages state
        setIntroMessages(updatedIntroMessages);
        
        // Always transition after first message - wait for message to render
        setTimeout(() => {
          // Move animation to background with smooth enlargement
          setAnimationPosition('background');
          setTimeout(() => {
            setShowIntro(false);
            setChatActive(true);
            // Move intro messages to conversation log
            setConversationLog(updatedIntroMessages);
            setIntroMessages([]);
            setWaitingForFirstResponse(false);
            setIsLoading(false);
          }, 300);
        }, 500);
      } else {
        addToLog('Giva', responseText, 'ai');
        setIsLoading(false);
      }
      
      // Check if call is required
      if (aiResponse.call_info && aiResponse.call_info.requires_call) {
        setCallInfo(aiResponse.call_info);
        setShowCallModal(true);
        // Pre-fill phone if extracted
        if (aiResponse.call_info.extracted_info?.phone_number) {
          setPatientPhone(aiResponse.call_info.extracted_info.phone_number);
        }
      }
      
      // Only speak if we have a valid response and not transitioning
      if (responseText && !isFirstMessage) {
        await speakWithDeepgram(responseText);
      } else if (responseText && isFirstMessage) {
        // For first message, wait for transition then speak
        setTimeout(async () => {
          await speakWithDeepgram(responseText);
        }, 1000);
      }
      
    } catch (error) {
      const errorMessage = error.message || 'Failed to get response from AI. Please try again.';
      
      if (isFirstMessage) {
        // Even on error, transition to chat page
        const errorMessageLog = {
          speaker: 'System',
          message: `Error: ${errorMessage}`,
          type: 'system',
          timestamp: new Date().toLocaleTimeString()
        };
        const updatedIntroMessages = [userMessageLog, errorMessageLog];
        setIntroMessages(updatedIntroMessages);
        
        // Transition even on error
        setTimeout(() => {
          setAnimationPosition('background');
          setTimeout(() => {
            setShowIntro(false);
            setChatActive(true);
            setConversationLog(updatedIntroMessages);
            setIntroMessages([]);
            setWaitingForFirstResponse(false);
            setIsLoading(false);
          }, 300);
        }, 500);
      } else {
        addToLog('System', `Error: ${errorMessage}`, 'system');
        setIsLoading(false);
      }
      
      console.error('Error handling user message:', error);
      
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

    // Don't hide intro immediately - wait for first response
    // This is handled in handleUserMessage

    // Reset inactivity timer
    lastInteractionRef.current = Date.now();
    setShowTimeoutPopup(false);

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

  const handleIntroSubmit = (e) => {
    e.preventDefault();
    if (inputMessage.trim()) {
      handleUserMessage(inputMessage.trim());
    }
  };

  return (
    <div className="app-container">
      {/* Background Image Animation */}
      <div className={`image-animation-container theme-${theme} ${animationPosition}`}>
        <img
          src={imageSequence[currentImageIndex]}
          alt="Animated background"
          className="animated-image fade-in"
          key={currentImageIndex}
        />
      </div>

      {/* Theme Toggle Button */}
      <button 
        className="theme-toggle-button"
        onClick={toggleTheme}
        aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
        title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
      >
        {theme === 'light' ? <Moon className="theme-icon" /> : <Sun className="theme-icon" />}
      </button>

      {/* Intro Page */}
      {showIntro && (
        <div className={`intro-page theme-${theme}`}>
          <div className="intro-content">
            {/* Centered animation during intro */}
            {introMessages.length === 0 && (
              <div className="intro-center-animation">
                <img
                  src={imageSequence[currentImageIndex]}
                  alt="Premium animation"
                  className="intro-center-animated-image"
                  key={currentImageIndex}
                />
              </div>
            )}
            
            {/* Text below animation - only show if no messages */}
            {introMessages.length === 0 && (
              <div className="intro-text">
                <h2 className="intro-title">Say "Giva" to activate</h2>
                <p className="intro-subtitle">Or type your message below</p>
              </div>
            )}
            
            {/* Messages area - show when messages exist */}
            {introMessages.length > 0 && (
              <div className="intro-messages-container">
                {introMessages.map((log, index) => (
                  <div key={index} className={`intro-message-wrapper ${log.type}`}>
                    {log.type === 'ai' && (
                      <img 
                        src={profilePhoto} 
                        alt="Giva" 
                        className="intro-profile-photo"
                      />
                    )}
                    <div className={`intro-message ${log.type}`}>
                      <div className="intro-message-header">
                        <span className="intro-message-speaker">{log.speaker}</span>
                        <span className="intro-message-time">{log.timestamp}</span>
                      </div>
                      <div className="intro-message-content">{log.message}</div>
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="intro-message-wrapper ai">
                    <img 
                      src={profilePhoto} 
                      alt="Giva" 
                      className="intro-profile-photo"
                    />
                    <div className="intro-message ai">
                      <div className="intro-message-content">
                        <span className="typing-indicator">Giva is thinking...</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {/* Input form */}
            <form onSubmit={handleIntroSubmit} className="intro-input-form">
              <input
                type="text"
                className="intro-text-input"
                placeholder="Type your message here..."
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                autoFocus
                disabled={waitingForFirstResponse}
              />
              <button 
                type="submit" 
                className="intro-submit-button"
                disabled={waitingForFirstResponse || !inputMessage.trim()}
              >
                <Send className="icon" />
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Chat Container - Hidden during intro */}
      {!showIntro && (
        <div className={`chat-container theme-${theme} ${chatActive ? 'active' : ''}`}>

        <div className="chat-messages">
          {conversationLog.length === 0 && (
            <div className="empty-state">
              <Mic className="empty-icon" />
              <p className="empty-title">Say "giva" to activate</p>
              <p className="empty-subtitle">Or type a message below to start chatting</p>
            </div>
          )}
          
          {conversationLog.map((log, index) => (
            <div key={index} className={`message-wrapper ${log.type}`}>
              {log.type === 'ai' && (
                <img 
                  src={profilePhoto} 
                  alt="Giva" 
                  className="message-profile-photo"
                />
              )}
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
              <img 
                src={profilePhoto} 
                alt="Giva" 
                className="message-profile-photo"
              />
              <div className="message ai">
                <div className="message-content">
                  <span className="typing-indicator">Giva is thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Timeout Popup - positioned above mic button */}
        {showTimeoutPopup && (
          <div className={`timeout-popup theme-${theme}`}>
            <div className={`timeout-popup-content theme-${theme}`}>
              <p className="timeout-popup-text">Say "Giva" to activate</p>
            </div>
          </div>
        )}

        {/* Call Modal */}
        {showCallModal && callInfo && (
          <div className={`call-modal theme-${theme}`} onClick={() => setShowCallModal(false)}>
            <div className={`call-modal-content theme-${theme}`} onClick={(e) => e.stopPropagation()}>
              <button className="call-modal-close" onClick={() => setShowCallModal(false)}>
                <X className="icon" />
              </button>
              <div className="call-modal-header">
                <Phone className="call-modal-icon" />
                <h3 className="call-modal-title">
                  {callInfo.intent === 'cancel' ? 'Cancel Appointment' : 'Reschedule Appointment'}
                </h3>
                <p className="call-modal-subtitle">
                  We'll call the patient to {callInfo.intent === 'cancel' ? 'confirm cancellation' : 'find a better time'}.
                </p>
              </div>
              <div className="call-modal-form">
                <div className="call-modal-field">
                  <label className="call-modal-label">Patient Phone Number *</label>
                  <input
                    type="tel"
                    className="call-modal-input"
                    placeholder="+1234567890"
                    value={patientPhone}
                    onChange={(e) => setPatientPhone(e.target.value)}
                    autoFocus
                  />
                </div>
                <div className="call-modal-field">
                  <label className="call-modal-label">Patient Name (Optional)</label>
                  <input
                    type="text"
                    className="call-modal-input"
                    placeholder="John Doe"
                    value={patientName}
                    onChange={(e) => setPatientName(e.target.value)}
                  />
                </div>
                <div className="call-modal-actions">
                  <button
                    className="call-modal-cancel"
                    onClick={() => {
                      setShowCallModal(false);
                      setPatientPhone('');
                      setPatientName('');
                      setCallInfo(null);
                    }}
                    disabled={isCalling}
                  >
                    Cancel
                  </button>
                  <button
                    className="call-modal-submit"
                    onClick={initiateCall}
                    disabled={!patientPhone.trim() || isCalling}
                  >
                    {isCalling ? 'Calling...' : 'Initiate Call'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

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
              placeholder={isListening ? 'Listening...' : isWakeWordMode ? 'Say "giva" or type a message...' : 'Type your message here...'}
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
          
          
        </div>
        </div>
      )}
    </div>
  );
};

export default DentalVoiceAI;