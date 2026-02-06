import { staticUrl } from '../config';
import './About.css';

function About() {
  return (
    <div className="about">
      <div className="about-image">
        <img src={staticUrl('kungfuchess.jpg')} alt="Original Clutch Chess" />
        <div className="about-image-caption">The original Clutch Chess.</div>
      </div>
      <div className="about-text">
        <p>
          Clutch Chess is a variant of chess designed for the internet age. It brings the real-time strategy aspect
          of games like StarCraft, Command &amp; Conquer, and Age of Empires to a classic setting. It was originally
          released in 2002 by Shizmoo Games and was popular through the mid-2000s. This is a reinvention of the game
          using modern technology and game design to bring out its potential. I hope you enjoy playing!
        </p>

        <p>
          If you have feedback, please stop by our{' '}
          <a href="https://www.reddit.com/r/clutchchess/" target="_blank" rel="noopener noreferrer">reddit</a> or reach out to{' '}
          <a href="mailto:contact@clutchchess.com">contact@clutchchess.com</a>.
        </p>
      </div>
    </div>
  );
}

export default About;
