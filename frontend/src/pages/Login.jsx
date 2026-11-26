import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { institutionApi } from '../api/institution';
import { extractApiError } from '../utils/format';
import LegalModal from '../components/LegalModal';

export default function Login() {
  const [isLoginTab, setIsLoginTab] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [selectedRole, setSelectedRole] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [statusNotification, setStatusNotification] = useState(null);
  const [legalModalDoc, setLegalModalDoc] = useState(null);

  // Claim Roster State
  const [admissionNumber, setAdmissionNumber] = useState('');
  const [classId, setClassId] = useState('1');
  const [regPassword, setRegPassword] = useState('');
  const [showRegPassword, setShowRegPassword] = useState(false);
  const [contactEmail, setContactEmail] = useState('');
  const [classes, setClasses] = useState([]);

  const { login, registerStudent, user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';
  const navigate = useNavigate();
  const canvasRef = useRef(null);

  // Redirect if already authenticated
  useEffect(() => {
    if (user && user.role) {
      if (user.role === 'ADMINISTRATOR') navigate('/admin', { replace: true });
      else if (user.role === 'TEACHER') navigate('/teacher', { replace: true });
      else if (user.role === 'STUDENT') navigate('/student', { replace: true });
    }
  }, [user, navigate]);

  // Load classes for roster claim dropdown only when claiming roster
  useEffect(() => {
    if (!isLoginTab && classes.length === 0) {
      institutionApi
        .getClasses()
        .then((cls) => {
          if (Array.isArray(cls) && cls.length > 0) {
            setClasses(cls);
            setClassId(String(cls[0].id));
          }
        })
        .catch(() => {});
    }
  }, [isLoginTab, classes.length]);

  // Quick Demo Profiles
  const demoProfiles = {
    admin: {
      id: 'admin',
      pass: 'Admin@123',
      role: 'Admin',
      badgeClass: 'bg-purple-100 text-purple-800',
    },
    teacher: {
      id: 'teacher_sarah',
      pass: 'Teacher@123',
      role: 'Teacher (Grade 10 Lead)',
      badgeClass: 'bg-emerald-100 text-emerald-800',
    },
    student: {
      id: 'STU1001',
      pass: 'Student@123',
      role: 'Student (Alex Carter • STU1001)',
      badgeClass: 'bg-sky-100 text-sky-800',
    },
  };

  const populateDemo = (roleKey) => {
    const profile = demoProfiles[roleKey];
    if (!profile) return;
    setUsername(profile.id);
    setPassword(profile.pass);
    setSelectedRole({ name: profile.role, badgeClass: profile.badgeClass });
    setError('');
    setStatusNotification(null);
  };

  // Login handler
  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setStatusNotification(null);
    setLoading(true);

    try {
      const res = await login(username, password);
      setStatusNotification({
        type: 'success',
        title: 'Authentication Handshake Initiated',
        message: `Establishing secure session token for ${username}. Redirecting to Analytics Dashboard...`,
      });
      setTimeout(() => {
        if (res?.role === 'ADMINISTRATOR') {
          navigate('/admin', { replace: true });
        } else if (res?.role === 'TEACHER') {
          navigate('/teacher', { replace: true });
        } else if (res?.role === 'STUDENT') {
          navigate('/student', { replace: true });
        } else {
          navigate('/', { replace: true });
        }
      }, 350);
    } catch (err) {
      setError(extractApiError(err, 'Invalid username or password.'));
      setLoading(false);
    }
  };

  // Student Claim handler
  const handleClaim = async (e) => {
    e.preventDefault();
    setError('');
    setStatusNotification(null);

    const parsedClassId = parseInt(classId, 10);
    if (!parsedClassId || parsedClassId < 1) {
      setError('Please provide a valid Class ID.');
      return;
    }

    if (regPassword.length < 8 || regPassword.length > 72) {
      setError('Password must be between 8 and 72 characters.');
      return;
    }

    setLoading(true);
    try {
      const res = await registerStudent({
        admission_number: admissionNumber.trim(),
        class_id: parsedClassId,
        password: regPassword,
        contact_email: contactEmail.trim() || null,
      });

      // Uniform 202 anti-enumeration notification
      setStatusNotification({
        type: 'anti-enumeration',
        title: 'HTTP 202 Accepted: Verification Token Dispatched',
        message:
          res.message ||
          `If ${admissionNumber.trim()} corresponds to an unverified student record, an activation OTP link has been sent to ${
            contactEmail || 'your registered contact'
          }. Response is uniform to prevent account enumeration.`,
      });

      setAdmissionNumber('');
      setRegPassword('');
      setContactEmail('');
    } catch (err) {
      setError(extractApiError(err, 'Registration failed. Please check inputs.'));
    } finally {
      setLoading(false);
    }
  };

  // Chalk Trail Canvas Engine with Theme Awareness
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let width = window.innerWidth;
    let height = window.innerHeight;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);

    function resize() {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = width + 'px';
      canvas.style.height = height + 'px';
      ctx.scale(dpr, dpr);
    }
    resize();
    window.addEventListener('resize', resize, { passive: true });

    // Palettes
    const darkChalkColors = [
      { r: 248, g: 250, b: 252 }, // Chalk white
      { r: 56, g: 189, b: 248 },  // Cyan 400
      { r: 129, g: 140, b: 248 }, // Indigo 400
      { r: 224, g: 242, b: 254 }, // Sky 100
      { r: 252, g: 211, b: 77 },  // Accent warm gold dust
    ];

    const lightChalkColors = [
      { r: 53, g: 37, b: 205 },   // Primary indigo
      { r: 2, g: 132, b: 199 },   // Sapphire 600
      { r: 30, g: 41, b: 59 },    // Slate graphite
      { r: 79, g: 70, b: 229 },   // Vibrant indigo
      { r: 217, g: 119, b: 6 },   // Warm amber chalk
    ];

    const strokes = [];
    const particles = [];
    const MAX_STROKES = prefersReducedMotion ? 15 : 120;
    const MAX_PARTICLES = prefersReducedMotion ? 25 : 250;

    let lastX = null;
    let lastY = null;
    let isMouseDown = false;
    let animId = null;

    class ChalkSegment {
      constructor(x1, y1, x2, y2, color, strokeW, isBurst) {
        this.x1 = x1;
        this.y1 = y1;
        this.x2 = x2;
        this.y2 = y2;
        this.color = color;
        this.width = strokeW;
        this.maxLife = isBurst ? 90 : 70;
        this.life = this.maxLife;
        this.isBurst = isBurst;
      }
      update() {
        this.life--;
        return this.life > 0;
      }
      draw(c) {
        const progress = this.life / this.maxLife;
        const alpha = Math.pow(progress, 1.4) * (this.isBurst ? 0.75 : 0.48);
        c.save();
        c.beginPath();
        c.moveTo(this.x1, this.y1);
        c.lineTo(this.x2, this.y2);
        c.strokeStyle = `rgba(${this.color.r}, ${this.color.g}, ${this.color.b}, ${alpha})`;
        c.lineWidth = this.width * (0.6 + progress * 0.4);
        c.lineCap = 'round';
        c.lineJoin = 'round';
        c.shadowColor = `rgba(${this.color.r}, ${this.color.g}, ${this.color.b}, ${alpha * 0.5})`;
        c.shadowBlur = this.isBurst ? 6 : 3;
        c.stroke();
        c.restore();
      }
    }

    class ChalkDust {
      constructor(x, y, vx, vy, color, size, lifeSpan) {
        this.x = x;
        this.y = y;
        this.vx = vx;
        this.vy = vy;
        this.color = color;
        this.size = size;
        this.maxLife = lifeSpan;
        this.life = lifeSpan;
        this.rotation = Math.random() * Math.PI * 2;
        this.spin = (Math.random() - 0.5) * 0.08;
      }
      update() {
        this.x += this.vx;
        this.y += this.vy;
        this.vx *= 0.94;
        this.vy = this.vy * 0.94 - 0.02;
        this.rotation += this.spin;
        this.life--;
        return this.life > 0;
      }
      draw(c) {
        const progress = this.life / this.maxLife;
        const alpha = Math.min(1, Math.sin(progress * Math.PI)) * 0.65;
        c.save();
        c.translate(this.x, this.y);
        c.rotate(this.rotation);
        c.fillStyle = `rgba(${this.color.r}, ${this.color.g}, ${this.color.b}, ${alpha})`;
        const s = Math.max(0.5, this.size * progress);
        c.fillRect(-s / 2, -s / 2, s, s * (0.8 + Math.random() * 0.4));
        c.restore();
      }
    }

    function spawnChalk(currentX, currentY, isBurst = false) {
      if (prefersReducedMotion) return;
      const palette = isDark ? darkChalkColors : lightChalkColors;
      const color = palette[Math.floor(Math.random() * palette.length)];

      if (lastX !== null && lastY !== null) {
        const dist = Math.hypot(currentX - lastX, currentY - lastY);
        if (dist > 1.5) {
          const strokeWidth = isBurst ? Math.random() * 3.5 + 2.5 : Math.random() * 2 + 1.2;
          strokes.push(new ChalkSegment(lastX, lastY, currentX, currentY, color, strokeWidth, isBurst));
          if (strokes.length > MAX_STROKES) strokes.shift();
        }
      }

      const particleCount = isBurst ? 5 : Math.random() < 0.75 ? 2 : 1;
      for (let i = 0; i < particleCount; i++) {
        const angle = Math.random() * Math.PI * 2;
        const speed = (Math.random() * 1.6 + 0.3) * (isBurst ? 2.2 : 1);
        const vx = Math.cos(angle) * speed + (Math.random() - 0.5) * 0.4;
        const vy = Math.sin(angle) * speed - (Math.random() * 0.6 + 0.2);
        const pColor = palette[Math.floor(Math.random() * palette.length)];
        const size = Math.random() * (isBurst ? 3.5 : 2.2) + 0.8;
        const lifeSpan = Math.floor(Math.random() * 45 + 50);

        particles.push(
          new ChalkDust(
            currentX + (Math.random() - 0.5) * 10,
            currentY + (Math.random() - 0.5) * 10,
            vx,
            vy,
            pColor,
            size,
            lifeSpan
          )
        );
        if (particles.length > MAX_PARTICLES) particles.shift();
      }

      lastX = currentX;
      lastY = currentY;
    }

    const onMouseMove = (e) => spawnChalk(e.clientX, e.clientY, isMouseDown);
    const onMouseDown = (e) => {
      isMouseDown = true;
      lastX = e.clientX;
      lastY = e.clientY;
      spawnChalk(e.clientX, e.clientY, true);
    };
    const onMouseUp = () => {
      isMouseDown = false;
    };
    const onMouseLeave = () => {
      lastX = null;
      lastY = null;
      isMouseDown = false;
    };

    window.addEventListener('mousemove', onMouseMove, { passive: true });
    window.addEventListener('mousedown', onMouseDown, { passive: true });
    window.addEventListener('mouseup', onMouseUp, { passive: true });
    window.addEventListener('mouseleave', onMouseLeave);

    function render() {
      ctx.clearRect(0, 0, width, height);

      for (let i = strokes.length - 1; i >= 0; i--) {
        const s = strokes[i];
        if (s.update()) {
          s.draw(ctx);
        } else {
          strokes.splice(i, 1);
        }
      }

      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        if (p.update()) {
          p.draw(ctx);
        } else {
          particles.splice(i, 1);
        }
      }

      animId = requestAnimationFrame(render);
    }
    animId = requestAnimationFrame(render);

    return () => {
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mouseup', onMouseUp);
      window.removeEventListener('mouseleave', onMouseLeave);
      if (animId) cancelAnimationFrame(animId);
    };
  }, [isDark]);

  return (
    <div className="min-h-screen blackboard-bg chalk-grid text-slate-100 font-sans flex flex-col justify-between selection:bg-indigo-600 selection:text-white relative overflow-x-hidden transition-colors duration-400">
      {/* Interactive Chalk Drawing Canvas Layer */}
      <canvas
        ref={canvasRef}
        id="chalk-canvas"
        className="fixed inset-0 pointer-events-none z-10 w-full h-full"
      />

      {/* 1. Ambient Chalk Dust & Floating Academic Glyphs Canvas */}
      <div
        className="fixed inset-0 pointer-events-none select-none z-0 overflow-hidden"
        data-purpose="chalk-particles-field"
      >
        {/* Glowing soft chalk motes */}
        <div className="absolute top-1/4 left-1/5 w-2 h-2 rounded-full bg-cyan-200/50 dark:bg-cyan-200/50 bg-indigo-500/40 blur-[1px] animate-dust-1" />
        <div className="absolute top-3/5 left-1/3 w-3 h-3 rounded-full bg-indigo-300/40 dark:bg-indigo-300/40 bg-sky-500/35 blur-[1.5px] animate-dust-2" />
        <div className="absolute top-1/6 right-1/4 w-2 h-2 rounded-full bg-sky-200/50 dark:bg-sky-200/50 bg-indigo-400/40 blur-[1px] animate-dust-3" />
        <div className="absolute bottom-1/5 right-1/5 w-2.5 h-2.5 rounded-full bg-amber-200/40 dark:bg-amber-200/40 bg-amber-500/35 blur-[1px] animate-dust-1" />
        <div className="absolute top-2/3 right-1/3 w-1.5 h-1.5 rounded-full bg-cyan-100/60 dark:bg-cyan-100/60 bg-indigo-600/30 blur-[0.5px] animate-dust-2" />

        {/* Mathematical Chalk Glyphs drifting slowly */}
        <div
          className="absolute top-[16%] left-[8%] text-2xl font-serif text-cyan-200/20 dark:text-cyan-200/20 text-indigo-900/20 select-none animate-dust-1 italic"
        >
          ∫
        </div>
        <div className="absolute top-[38%] left-[16%] text-xl font-mono text-indigo-200/20 dark:text-indigo-200/20 text-indigo-900/20 select-none animate-dust-3">
          ∑
        </div>
        <div
          className="absolute bottom-[28%] left-[7%] text-2xl font-serif text-sky-300/20 dark:text-sky-300/20 text-indigo-900/20 select-none animate-dust-2 italic"
        >
          π
        </div>
        <div className="absolute top-[22%] right-[14%] text-xl font-mono text-cyan-200/25 dark:text-cyan-200/25 text-sky-900/20 select-none animate-dust-2">
          Δ
        </div>
        <div
          className="absolute top-[48%] right-[8%] text-lg font-serif text-indigo-200/25 dark:text-indigo-200/25 text-indigo-900/20 select-none animate-dust-1 italic"
        >
          f(x)
        </div>
        <div
          className="absolute bottom-[22%] right-[18%] text-xl font-serif text-sky-200/20 dark:text-sky-200/20 text-sky-900/20 select-none animate-dust-3 italic"
        >
          α
        </div>
        <div
          className="absolute bottom-[40%] right-[24%] text-base font-mono text-cyan-300/20 dark:text-cyan-300/20 text-indigo-800/20 select-none animate-dust-2"
        >
          λ
        </div>
        <div className="absolute top-[75%] left-[22%] text-lg font-mono text-indigo-300/20 dark:text-indigo-300/20 text-indigo-900/20 select-none animate-dust-1">
          θ
        </div>
      </div>

      {/* 2. Batik & Damask Pattern Wings (Left & Right Side Shimmer) */}
      <div
        className="fixed left-0 top-0 bottom-0 w-64 lg:w-96 pointer-events-none select-none z-0 opacity-20 dark:opacity-20 opacity-15 animate-pulse-glow"
        data-purpose="batik-motif-left"
      >
        <svg
          className="w-full h-full text-indigo-400 dark:text-indigo-400 text-indigo-600 stroke-current"
          fill="none"
          preserveAspectRatio="none"
          viewBox="0 0 380 900"
        >
          <defs>
            <pattern height="80" id="batik-pattern" patternUnits="userSpaceOnUse" width="80" x="0" y="0">
              <path
                d="M40 0 C52 16 68 28 80 40 C68 52 52 64 40 80 C28 64 12 52 0 40 C12 28 28 16 40 0 Z"
                fill="rgba(56, 189, 248, 0.03)"
                stroke="rgba(99, 102, 241, 0.45)"
                strokeWidth="1.2"
              />
              <path
                d="M40 14 C48 26 58 34 66 40 C58 46 48 54 40 66 C32 54 22 46 14 40 C22 34 32 26 40 14 Z"
                fill="none"
                stroke="rgba(56, 189, 248, 0.35)"
                strokeWidth="0.9"
              />
              <circle cx="40" cy="40" fill="rgba(99, 102, 241, 0.5)" r="4" />
              <circle cx="0" cy="0" fill="rgba(56, 189, 248, 0.4)" r="3" />
              <circle cx="80" cy="0" fill="rgba(56, 189, 248, 0.4)" r="3" />
              <circle cx="0" cy="80" fill="rgba(56, 189, 248, 0.4)" r="3" />
              <circle cx="80" cy="80" fill="rgba(56, 189, 248, 0.4)" r="3" />
              <path
                d="M40 25 Q46 32 40 40 Q34 48 40 55"
                stroke="rgba(199, 210, 254, 0.3)"
                strokeLinecap="round"
                strokeWidth="1"
              />
              <path
                d="M25 40 Q32 34 40 40 Q48 46 55 40"
                stroke="rgba(199, 210, 254, 0.3)"
                strokeLinecap="round"
                strokeWidth="1"
              />
            </pattern>
          </defs>
          <rect fill="url(#batik-pattern)" height="100%" width="100%" />
        </svg>
      </div>

      <div
        className="fixed right-0 top-0 bottom-0 w-64 lg:w-96 pointer-events-none select-none z-0 opacity-20 dark:opacity-20 opacity-15 animate-pulse-glow"
        data-purpose="batik-motif-right"
        style={{ animationDelay: '-3.5s' }}
      >
        <svg
          className="w-full h-full text-sky-400 dark:text-sky-400 text-sky-600 stroke-current"
          fill="none"
          preserveAspectRatio="none"
          viewBox="0 0 380 900"
        >
          <rect
            fill="url(#batik-pattern)"
            height="100%"
            transform="scale(-1, 1) translate(-380, 0)"
            width="100%"
          />
        </svg>
      </div>

      {/* 3. Left Side Academic Chalkboard Illustration */}
      <div
        className="fixed left-4 lg:left-12 top-1/2 -translate-y-1/2 pointer-events-none hidden md:block select-none z-0 opacity-90"
        data-purpose="left-analytic-illustration"
      >
        <div className="relative w-64 lg:w-80 h-[520px]">
          {/* Minimalist Indigo/Cyan Polka Block in Chalk Frame */}
          <div className="illustration-chalk-card absolute bottom-12 left-4 w-28 h-44 rounded-2xl bg-slate-900/60 border border-indigo-400/40 p-3 overflow-hidden shadow-lg backdrop-blur-md flex flex-wrap gap-3 content-start transition-all duration-300">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400/70" />
          </div>

          {/* Chalk Line Graph & Growth Indicator card */}
          <div className="illustration-chalk-card absolute bottom-6 left-28 w-24 h-24 bg-slate-900/75 backdrop-blur-lg rounded-xl border border-sky-400/50 p-2.5 shadow-lg shadow-sky-950/40 transition-all duration-300">
            <svg className="w-full h-full text-cyan-400 dark:text-cyan-300" viewBox="0 0 80 80">
              <polyline
                className="chalk-line-anim"
                fill="none"
                points="10,65 30,45 50,52 70,18"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2.5"
              />
              <polyline
                fill="none"
                points="56,18 70,18 70,32"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2.5"
              />
              <circle className="animate-pulse" cx="70" cy="18" fill="#38bdf8" r="3.5" />
            </svg>
          </div>

          {/* Academic Card Mockup Doodle in Chalk Style */}
          <div className="illustration-chalk-card absolute top-20 left-6 w-36 h-28 bg-slate-900/70 backdrop-blur-lg rounded-xl border border-indigo-300/40 p-3 shadow-lg flex flex-col justify-center gap-2 transition-all duration-300">
            <div className="w-12 h-2 rounded bg-indigo-400/60" />
            <div className="w-24 h-1.5 rounded bg-slate-400/50" />
            <div className="w-18 h-1.5 rounded bg-slate-400/50" />
            <div className="flex items-center gap-1.5 mt-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span className="text-[9px] font-mono text-cyan-300 dark:text-cyan-200/80 illustration-text-contrast">
                98.4% Acc.
              </span>
            </div>
          </div>

          {/* Mathematical Wave & Node SVGs */}
          <svg
            className="absolute inset-0 w-full h-full text-sky-400/60 dark:text-sky-400/60 text-sky-600/50 stroke-current"
            fill="none"
            viewBox="0 0 320 520"
          >
            <path d="M 30,90 Q 70,50 110,85 T 190,75" strokeDasharray="3 4" strokeWidth="2" />
            <path d="M 60,340 C 90,300 130,420 180,360" stroke="rgba(99, 102, 241, 0.7)" strokeWidth="2" />
            <circle cx="200" cy="80" fill="#38bdf8" r="4.5" />
            <circle cx="45" cy="270" fill="none" r="4" stroke="#818cf8" strokeWidth="1.8" />
            <path d="M 120,400 Q 150,380 180,410 T 240,395" strokeDasharray="4 3" strokeWidth="1.8" />
          </svg>
        </div>
      </div>

      {/* 4. Right Side Academic Illustration: Student with Laptop & Cohort Node */}
      <div
        className="fixed right-4 lg:right-12 top-1/2 -translate-y-1/2 pointer-events-none hidden md:block select-none z-0 opacity-90"
        data-purpose="right-analytic-illustration"
      >
        <div className="relative w-64 lg:w-80 h-[520px]">
          {/* Right Pattern Pillar in deep chalkboard framing */}
          <div className="illustration-chalk-card absolute bottom-10 right-4 w-24 h-40 rounded-2xl bg-slate-900/60 border border-sky-400/40 p-3 shadow-lg backdrop-blur-md flex flex-wrap gap-3 content-start transition-all duration-300">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400/70" />
          </div>

          {/* Pedestal / Modern Minimalist Student Line Art */}
          <div className="illustration-chalk-card absolute bottom-10 right-28 w-28 h-56 bg-slate-900/75 backdrop-blur-lg rounded-xl border border-indigo-400/40 p-2 flex flex-col justify-end shadow-xl transition-all duration-300">
            <div className="w-full text-center text-[10px] text-cyan-400 dark:text-cyan-300 font-mono tracking-wider mb-2 illustration-text-contrast">
              EDWISE.DESK
            </div>
          </div>

          {/* Stylized Academic / Student Chalk Silhouette SVG */}
          <svg
            className="absolute bottom-28 right-20 w-44 h-56 text-slate-100 transition-colors"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 160 200"
          >
            <circle className="student-svg-head" cx="85" cy="40" fill="#e2e8f0" r="14" />
            <path
              className="student-svg-body"
              d="M 75,54 C 65,70 55,90 60,110 L 95,110 L 90,75 Z"
              fill="#cbd5e1"
              stroke="#ffffff"
              strokeWidth="2"
            />
            <path
              d="M 60,105 L 45,150 L 55,160 L 75,135 L 85,155"
              stroke="#94a3b8"
              strokeLinecap="round"
              strokeWidth="2.5"
            />
            {/* Laptop / Tablet with Soft Teal Screen Glow */}
            <path d="M 38,98 L 56,108 L 48,118 Z" fill="#38bdf8" stroke="#0284c7" strokeWidth="2" />
            <path d="M 52,90 L 40,98" stroke="#38bdf8" strokeLinecap="round" strokeWidth="2" />
          </svg>

          {/* Float Analytics Glass Node */}
          <div className="illustration-chalk-card absolute top-16 right-8 w-44 bg-slate-900/85 backdrop-blur-xl rounded-xl p-3 shadow-xl border border-sky-400/50 flex flex-col gap-1.5 animate-float-slow transition-all duration-300">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-100 dark:text-slate-100 illustration-text-contrast">
                Cohort Insight
              </span>
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 ring-2 ring-emerald-400/40 animate-pulse" />
            </div>
            <div className="h-1.5 w-full bg-slate-800 dark:bg-slate-800 bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-sky-400 to-indigo-500 rounded-full w-4/5" />
            </div>
            <span className="text-[9px] text-cyan-300 dark:text-cyan-200 font-mono tracking-tight illustration-text-contrast">
              Active Sync: Section 10-A
            </span>
          </div>

          <svg
            className="absolute inset-0 w-full h-full text-indigo-300/60 dark:text-indigo-300/60 text-indigo-500/40 stroke-current pointer-events-none"
            fill="none"
            viewBox="0 0 320 520"
          >
            <path d="M 120,40 Q 150,15 190,45" strokeWidth="2" />
            <circle cx="210" cy="50" fill="#818cf8" r="3" />
          </svg>
        </div>
      </div>

      {/* HEADER BAR */}
      <header
        className="relative z-20 w-full max-w-7xl mx-auto px-6 py-6 flex items-center justify-between transition-colors duration-400"
        data-purpose="site-header"
      >
        {/* Brand Info */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-sky-500 to-cyan-300 flex items-center justify-center shadow-lg shadow-indigo-500/30 text-white ring-1 ring-white/20">
            <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15h-2v-2h2v2zm0-4h-2V7h2v6zm4 4h-2v-4h2v4zm0-6h-2V9h2v2z" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span
                id="header-brand-title"
                className="text-xl font-bold tracking-tight text-slate-900 dark:text-white leading-none drop-shadow-sm transition-colors"
              >
                EDWISE
              </span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 border border-indigo-400/30">
                v4.2
              </span>
            </div>
            <p
              id="header-brand-sub"
              className="text-xs text-slate-600 dark:text-slate-400 font-medium tracking-tight transition-colors"
            >
              Learning Analytics Platform
            </p>
          </div>
        </div>

        {/* Right Header Actions */}
        <div className="flex items-center gap-2.5 sm:gap-4 lg:gap-6">
          {/* Theme Toggle Button (Light Academic / Dark Chalkboard) */}
          <button
            id="theme-toggle-btn"
            type="button"
            onClick={toggleTheme}
            aria-label="Toggle visual theme"
            title="Toggle Light Academic / Dark Chalkboard theme"
            className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/90 dark:bg-slate-900/70 border border-slate-200/90 dark:border-slate-700/80 backdrop-blur-md text-xs font-semibold text-slate-700 dark:text-slate-200 shadow-sm hover:border-indigo-400/60 dark:hover:border-indigo-400/60 hover:bg-slate-50 dark:hover:bg-slate-800/80 transition-all duration-300 group cursor-pointer"
          >
            <span
              id="theme-toggle-icon-wrap"
              className="relative flex items-center justify-center w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-600 dark:text-indigo-300 transition-transform duration-300 group-hover:scale-110"
            >
              {isDark ? (
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                  />
                </svg>
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                  />
                </svg>
              )}
            </span>
            <span id="theme-toggle-label" className="hidden sm:inline-block font-medium tracking-tight text-[11px]">
              {isDark ? 'Dark Slate' : 'Light Academic'}
            </span>
            <span
              id="theme-toggle-indicator"
              className={`w-1.5 h-1.5 rounded-full shadow-sm transition-colors ${
                isDark ? 'bg-cyan-400' : 'bg-amber-500'
              }`}
            />
          </button>

          {/* Academic Session Pill */}
          <div
            id="header-session-pill"
            className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-white/80 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-700/80 backdrop-blur-md text-xs text-slate-700 dark:text-slate-300 shadow-sm transition-colors"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Session 2026-2027</span>
            <span className="text-slate-300 dark:text-slate-600">|</span>
            <span className="text-emerald-600 dark:text-emerald-400 font-medium">
              All Nodes Operational
            </span>
          </div>
        </div>
      </header>

      {/* MAIN CENTER GLASS CARD */}
      <main
        className="relative z-10 flex-1 flex items-center justify-center px-4 py-8 sm:py-12"
        data-purpose="login-roster-container"
      >
        <div className="w-full max-w-[490px] glass-surface-canvas rounded-3xl shadow-glass p-7 sm:p-9 relative overflow-hidden transition-all duration-300 text-slate-800">
          {/* Top Decorative Glow Orbs within card */}
          <div className="absolute -top-16 -right-16 w-36 h-36 bg-indigo-300/30 rounded-full blur-2xl pointer-events-none" />
          <div className="absolute -top-16 -left-16 w-36 h-36 bg-sky-200/40 rounded-full blur-2xl pointer-events-none" />

          {/* Tab Navigation */}
          <div
            className="relative bg-slate-100/90 p-1 rounded-2xl flex items-center mb-6 border border-slate-200/80 shadow-inner"
            data-purpose="form-tab-switcher"
          >
            <button
              id="tab-signin"
              type="button"
              onClick={() => {
                setIsLoginTab(true);
                setError('');
                setStatusNotification(null);
              }}
              className={`w-1/2 py-2.5 rounded-xl text-xs sm:text-sm font-semibold tracking-tight transition-all duration-200 flex items-center justify-center gap-1.5 cursor-pointer ${
                isLoginTab
                  ? 'text-slate-900 bg-white shadow-sm'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                />
              </svg>
              Sign In
            </button>
            <button
              id="tab-claim"
              type="button"
              onClick={() => {
                setIsLoginTab(false);
                setError('');
                setStatusNotification(null);
              }}
              className={`w-1/2 py-2.5 rounded-xl text-xs sm:text-sm font-semibold tracking-tight transition-all duration-200 flex items-center justify-center gap-1.5 cursor-pointer ${
                !isLoginTab
                  ? 'text-slate-900 bg-white shadow-sm'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                />
              </svg>
              Claim Student Roster
              <span className="w-2 h-2 rounded-full bg-indigo-500" />
            </button>
          </div>

          {/* Toast / Notification Container */}
          {statusNotification && (
            <div
              id="status-toast"
              role="alert"
              className={`mb-5 p-3.5 rounded-xl border text-xs flex items-start gap-2.5 transition-all duration-300 ${
                statusNotification.type === 'success'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                  : 'bg-amber-50 border-amber-200 text-amber-900'
              }`}
            >
              <span className="mt-0.5 flex-shrink-0">
                {statusNotification.type === 'success' ? (
                  <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                    />
                  </svg>
                )}
              </span>
              <div className="flex-1">
                <div className="font-semibold">{statusNotification.title}</div>
                <div className="text-slate-600 dark:text-slate-700 mt-0.5 leading-relaxed">
                  {statusNotification.message}
                </div>
              </div>
            </div>
          )}

          {/* Global error alert */}
          {error && (
            <div className="mb-5 p-3.5 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 text-xs flex items-center gap-2">
              <svg className="w-4 h-4 text-rose-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          {/* VIEW 1: SIGN IN FORM */}
          {isLoginTab ? (
            <div className="block transition-opacity duration-200" data-purpose="signin-module" id="signin-view">
              <div className="text-center mb-5">
                <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-900">
                  Institutional Login
                </h1>
                <p className="text-xs sm:text-sm text-slate-500 mt-1">
                  Hey, Enter your details to get sign in to your workspace
                </p>
              </div>

              {/* Quick Demo Preset Chips */}
              <div
                className="mb-5 bg-slate-50/80 dark:bg-slate-100/90 border border-slate-200/80 rounded-2xl p-2.5 shadow-sm"
                data-purpose="quick-credential-presets"
              >
                <div className="flex items-center justify-between mb-2 px-1">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    Quick Demo Profiles (Click to fill)
                  </span>
                  {selectedRole && (
                    <span
                      id="selected-role-badge"
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${selectedRole.badgeClass}`}
                    >
                      Role: {selectedRole.name}
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-1.5">
                  <button
                    type="button"
                    onClick={() => populateDemo('admin')}
                    className="px-2 py-1.5 rounded-lg bg-white border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/50 text-[11px] font-medium text-slate-700 transition flex items-center justify-center gap-1 shadow-xs cursor-pointer"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-500" /> Admin
                  </button>
                  <button
                    type="button"
                    onClick={() => populateDemo('teacher')}
                    className="px-2 py-1.5 rounded-lg bg-white border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/50 text-[11px] font-medium text-slate-700 transition flex items-center justify-center gap-1 shadow-xs cursor-pointer"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Teacher
                  </button>
                  <button
                    type="button"
                    onClick={() => populateDemo('student')}
                    className="px-2 py-1.5 rounded-lg bg-white border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/50 text-[11px] font-medium text-slate-700 transition flex items-center justify-center gap-1 shadow-xs cursor-pointer"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-sky-500" /> Student
                  </button>
                </div>
              </div>

              {/* Login Form */}
              <form id="login-form" onSubmit={handleLogin} className="space-y-4">
                {/* Username Input */}
                <div>
                  <label className="sr-only" htmlFor="login-id">
                    Enter Email / Institutional ID
                  </label>
                  <div className="relative">
                    <input
                      id="login-id"
                      name="login-id"
                      type="text"
                      required
                      value={username}
                      onChange={(e) => {
                        setUsername(e.target.value);
                        if (selectedRole) setSelectedRole(null);
                      }}
                      placeholder="e.g. admin or teacher_sarah"
                      className="w-full h-12 px-4 pr-10 text-xs sm:text-sm rounded-xl border border-slate-200 bg-white/95 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm"
                    />
                    <div className="absolute inset-y-0 right-0 pr-3.5 flex items-center pointer-events-none text-slate-400">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                        />
                      </svg>
                    </div>
                  </div>
                </div>

                {/* Password Input with Show/Hide toggle */}
                <div>
                  <label className="sr-only" htmlFor="login-password">
                    Passcode
                  </label>
                  <div className="relative">
                    <input
                      id="login-password"
                      name="login-password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        if (selectedRole) setSelectedRole(null);
                      }}
                      placeholder="••••••••"
                      className="w-full h-12 px-4 pr-16 text-xs sm:text-sm rounded-xl border border-slate-200 bg-white/95 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-xs font-semibold text-slate-500 hover:text-slate-800 cursor-pointer"
                    >
                      {showPassword ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>

                {/* Remember device Checkbox */}
                <div className="flex items-center text-xs pt-0.5">
                  <label className="flex items-center gap-2 cursor-pointer text-slate-600">
                    <input
                      type="checkbox"
                      defaultChecked
                      className="w-4 h-4 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500 focus:ring-offset-0"
                    />
                    <span>Remember device</span>
                  </label>
                </div>

                {/* Primary Sign In Button */}
                <button
                  type="submit"
                  name="Sign In to Portal"
                  aria-label="Sign In to Portal"
                  disabled={loading}
                  className="w-full h-12 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-700 hover:to-indigo-800 text-white font-semibold text-sm tracking-wide shadow-lg shadow-indigo-600/30 active:scale-[0.99] transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  <span>{loading ? 'Authenticating...' : 'Sign in to Workspace'}</span>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M14 5l7 7m0 0l-7 7m7-7H3" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                  </svg>
                </button>
              </form>
            </div>
          ) : (
            /* VIEW 2: STUDENT ROSTER CLAIM (Spec UI-001) */
            <div className="block transition-opacity duration-200" data-purpose="roster-claim-module" id="claim-view">
              <div className="text-center mb-5">
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/60 text-[11px] font-semibold mb-2">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                    />
                  </svg>
                  Self-Service Account Activation (Spec UI-001)
                </div>
                <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-900">
                  Claim Student Account
                </h2>
                <p className="text-xs sm:text-sm text-slate-500 mt-1">
                  Verify official institutional admission records to establish your portal login.
                </p>
              </div>

              <form id="claim-form" onSubmit={handleClaim} className="space-y-3.5">
                {/* Admission ID Input */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1" htmlFor="admission-no">
                    Official Admission Number <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="admission-no"
                    name="admission-no"
                    type="text"
                    required
                    value={admissionNumber}
                    onChange={(e) => setAdmissionNumber(e.target.value)}
                    placeholder="e.g. STU1003"
                    className="w-full h-11 px-3.5 text-xs sm:text-sm rounded-xl border border-slate-200 bg-white/95 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                  />
                </div>

                {/* Class / Grade Selector */}
                <div className="grid grid-cols-2 gap-2.5">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1" htmlFor="grade-level">
                      Enrolled Grade / Class <span className="text-rose-500">*</span>
                    </label>
                    <select
                      id="grade-level"
                      value={classId}
                      onChange={(e) => setClassId(e.target.value)}
                      className="w-full h-11 px-3 text-xs sm:text-sm rounded-xl border border-slate-200 bg-white/95 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                    >
                      {classes.length > 0 ? (
                        classes.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))
                      ) : (
                        <>
                          <option value="1">Grade 10 (Secondary)</option>
                          <option value="2">Grade 11 (Sr Secondary)</option>
                          <option value="3">Grade 12 (Sr Secondary)</option>
                          <option value="4">Grade 9 (Foundational)</option>
                        </>
                      )}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1" htmlFor="section-id">
                      Section / Cohort <span className="text-rose-500">*</span>
                    </label>
                    <select
                      id="section-id"
                      className="w-full h-11 px-3 text-xs sm:text-sm rounded-xl border border-slate-200 bg-white/95 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                    >
                      <option value="A">Section 10-A (Alpha)</option>
                      <option value="B">Section 10-B (Beta)</option>
                      <option value="C">Section 10-C (Gamma)</option>
                      <option value="D">Section 10-D (Delta)</option>
                    </select>
                  </div>
                </div>

                {/* Student Contact Email */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1" htmlFor="claim-contact">
                    Registered Student / Parent Email <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="claim-contact"
                    name="claim-contact"
                    type="email"
                    required
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    placeholder="alex.rivers@student.edwise.edu"
                    className="w-full h-11 px-3.5 text-xs sm:text-sm rounded-xl border border-slate-200 bg-white/95 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                  />
                </div>

                {/* Create Account Passcode */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1" htmlFor="new-passcode">
                    Set Security Passcode <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      id="new-passcode"
                      type={showRegPassword ? 'text' : 'password'}
                      required
                      value={regPassword}
                      onChange={(e) => setRegPassword(e.target.value)}
                      placeholder="Minimum 8 characters"
                      className="w-full h-11 px-3.5 pr-14 text-xs sm:text-sm rounded-xl border border-slate-200 bg-white/95 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowRegPassword(!showRegPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-xs font-semibold text-slate-500 hover:text-slate-800 cursor-pointer"
                    >
                      {showRegPassword ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>

                {/* Anti-Enumeration Notice Box */}
                <div
                  className="p-3 rounded-xl bg-sky-50 border border-sky-200 text-[11px] text-sky-900 flex items-start gap-2"
                  data-purpose="anti-enumeration-callout"
                >
                  <svg className="w-4 h-4 text-sky-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                    />
                  </svg>
                  <div>
                    <span className="font-bold">Anti-Enumeration Protocol Active:</span> In accordance with FERPA &amp; Section 4.1 security specifications, responses return a uniform <em>202 Accepted</em> regardless of record pre-existence to prevent identity scraping.
                  </div>
                </div>

                {/* Submit Activation Claim */}
                <button
                  type="submit"
                  name="Claim Student Record"
                  aria-label="Claim Student Record"
                  disabled={loading}
                  className="w-full h-11 rounded-xl bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-600 hover:to-indigo-700 text-white font-semibold text-sm shadow-md shadow-indigo-500/25 active:scale-[0.99] transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  <span>{loading ? 'Submitting...' : 'Submit Verification Claim'}</span>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                    />
                  </svg>
                </button>
              </form>

              <p className="text-center text-xs text-slate-500 mt-4">
                Already verified?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setIsLoginTab(true);
                    setError('');
                    setStatusNotification(null);
                  }}
                  className="font-semibold text-indigo-600 hover:text-indigo-700 hover:underline cursor-pointer"
                >
                  Return to Sign In
                </button>
              </p>
            </div>
          )}
        </div>
      </main>

      {/* FOOTER BAR */}
      <footer
        id="main-footer"
        className="relative z-20 w-full max-w-7xl mx-auto px-6 py-6 text-center text-xs text-slate-600 dark:text-slate-400 space-y-2 transition-colors duration-400"
        data-purpose="site-footer"
      >
        <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6 font-medium">
          <span className="inline-flex items-center gap-1 text-slate-700 dark:text-slate-300 transition-colors">
            <svg className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
              <path
                clipRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                fillRule="evenodd"
              />
            </svg>
            CBSE &amp; FERPA Compliant
          </span>
          <span className="text-slate-400 dark:text-slate-600">•</span>
          <span className="inline-flex items-center gap-1 text-slate-700 dark:text-slate-300 transition-colors">
            <svg className="w-3.5 h-3.5 text-sky-600 dark:text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
              />
            </svg>
            AES-256 Ledger Audited
          </span>
          <span className="text-slate-400 dark:text-slate-600">•</span>
          <button
            type="button"
            onClick={() => setLegalModalDoc('privacy')}
            className="text-slate-600 dark:text-slate-400 hover:text-black dark:hover:text-white transition-colors cursor-pointer underline-offset-2 hover:underline"
          >
            Privacy Policy
          </button>
          <span className="text-slate-400 dark:text-slate-600">•</span>
          <button
            type="button"
            onClick={() => setLegalModalDoc('terms')}
            className="text-slate-600 dark:text-slate-400 hover:text-black dark:hover:text-white transition-colors cursor-pointer underline-offset-2 hover:underline"
          >
            Terms of Service
          </button>
        </div>
        <p className="text-[11px] text-slate-500 dark:text-slate-500">
          Copyright © 2026 EDWISE Analytics Suite. All rights reserved. Authorized academic personnel only.
        </p>
      </footer>

      {/* Verified Backend Legal Document Modal */}
      <LegalModal
        isOpen={Boolean(legalModalDoc)}
        docType={legalModalDoc || 'privacy'}
        onClose={() => setLegalModalDoc(null)}
      />
    </div>
  );
}
