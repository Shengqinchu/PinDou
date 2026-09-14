import { gsap } from 'gsap';
import { reducedMotion } from './motion-preference';
import './motion';

/** One entrance per destination, independent of query state and image loading. */
export function enterRoute(main: HTMLElement, path: string) {
  if (reducedMotion() || !['/visit', '/shop', '/journal', '/details', '/tools'].includes(path)) return;
  return gsap.context(() => {
    const title = main.querySelectorAll('h1.lift-title > .lift-line');
    const timeline = gsap.timeline({ defaults: { ease: 'studio-travel' } });
    if (title.length) timeline.from(title, {
      y: 18, opacity: 0, duration: .85, stagger: .08,
      clearProps: 'transform,opacity',
    }, 0);
    const supporting: Record<string, string> = {
      '/visit': '.visit-progress',
      '/shop': '.shop-tabs',
      '/journal': '.journal-intro > div',
      '/details': '.vision-detail-nav',
      // The generator already animates its workspace when its draft is ready.
      '/tools': '.generator-heading nav',
    };
    const support = main.querySelector(supporting[path]);
    if (support) timeline.from(support, { y: 8, opacity: .55, duration: .72, clearProps: 'transform,opacity' }, .08);
    const surfaces: Record<string, string> = {
      '/visit': '.visit-scroll', '/shop': '.shop-layout',
      '/journal': '.journal-stories', '/details': '.vision-arrival',
    };
    const surface = surfaces[path] && main.querySelector(surfaces[path]);
    // Fade the form/grid in place: scroll containers, sticky children, and input
    // hit targets keep their geometry. Native clicks never wait for the timeline.
    if (surface) timeline.from(surface, { opacity: .6, duration: .65, clearProps: 'opacity' }, .12);
  }, main);
}
