'use client';

import { useEffect } from 'react';

/**
 * DOMGuard: Protects React against `NotFoundError: Failed to execute 'removeChild' on 'Node'`
 * and related DOM manipulation crashes caused by Google Translate, browser extensions,
 * third-party mapping libraries (Leaflet), and ad blockers.
 */
function applyDOMGuard() {
  if (typeof window === 'undefined' || typeof Node === 'undefined' || !Node.prototype) {
    return;
  }

  // Guard removeChild
  const originalRemoveChild = Node.prototype.removeChild;
  Node.prototype.removeChild = function <T extends Node>(child: T): T {
    if (child.parentNode !== this) {
      if (typeof console !== 'undefined' && console.warn) {
        console.warn('[DOMGuard] Suppressed removeChild: Node is not a direct child of this parent.', {
          parent: this,
          child,
          actualParent: child.parentNode,
        });
      }
      if (child.parentNode) {
        return child.parentNode.removeChild(child) as T;
      }
      return child;
    }
    return originalRemoveChild.call(this, child) as T;
  };

  // Guard insertBefore
  const originalInsertBefore = Node.prototype.insertBefore;
  Node.prototype.insertBefore = function <T extends Node>(newNode: T, referenceNode: Node | null): T {
    if (referenceNode && referenceNode.parentNode !== this) {
      if (typeof console !== 'undefined' && console.warn) {
        console.warn('[DOMGuard] Suppressed insertBefore: Reference node is not a direct child of this parent.', {
          parent: this,
          referenceNode,
          actualParent: referenceNode.parentNode,
        });
      }
      if (referenceNode.parentNode) {
        return referenceNode.parentNode.insertBefore(newNode, referenceNode) as T;
      }
      return this.appendChild(newNode) as T;
    }
    return originalInsertBefore.call(this, newNode, referenceNode) as T;
  };

  // Guard replaceChild
  const originalReplaceChild = Node.prototype.replaceChild;
  Node.prototype.replaceChild = function <T extends Node>(newChild: Node, oldChild: T): T {
    if (oldChild.parentNode !== this) {
      if (typeof console !== 'undefined' && console.warn) {
        console.warn('[DOMGuard] Suppressed replaceChild: Old child is not a direct child of this parent.', {
          parent: this,
          oldChild,
          actualParent: oldChild.parentNode,
        });
      }
      if (oldChild.parentNode) {
        return oldChild.parentNode.replaceChild(newChild, oldChild) as T;
      }
      return this.appendChild(newChild) as unknown as T;
    }
    return originalReplaceChild.call(this, newChild, oldChild) as T;
  };

  // Guard against extension attribute mutations (e.g. Bitdefender bis_skin_checked)
  if (typeof Element !== 'undefined' && Element.prototype) {
    const originalSetAttribute = Element.prototype.setAttribute;
    Element.prototype.setAttribute = function (name: string, value: string) {
      if (typeof name === 'string' && (name === 'bis_skin_checked' || name.startsWith('bis_'))) {
        return;
      }
      return originalSetAttribute.call(this, name, value);
    };

    const originalHasAttribute = Element.prototype.hasAttribute;
    Element.prototype.hasAttribute = function (name: string): boolean {
      if (typeof name === 'string' && (name === 'bis_skin_checked' || name.startsWith('bis_'))) {
        return false;
      }
      return originalHasAttribute.call(this, name);
    };

    const originalGetAttribute = Element.prototype.getAttribute;
    Element.prototype.getAttribute = function (name: string): string | null {
      if (typeof name === 'string' && (name === 'bis_skin_checked' || name.startsWith('bis_'))) {
        return null;
      }
      return originalGetAttribute.call(this, name);
    };
  }

  // Intercept Next.js / React hydration warning console errors
  if (typeof window !== 'undefined' && window.console) {
    const isNoise = (args: IArguments | unknown[]) => {
      for (let i = 0; i < args.length; i++) {
        const a = args[i];
        if (typeof a === 'string') {
          if (a.includes('bis_skin_checked') || a.includes('bis_')) return true;
        } else if (a && typeof a === 'object') {
          const err = a as Error;
          const str = `${err.message || ''} ${err.stack || ''} ${err.name || ''}`;
          if (str.includes('bis_skin_checked') || str.includes('bis_')) return true;
        }
      }
      return false;
    };

    const wrapFn = (target: (...args: unknown[]) => void) => {
      return function (this: unknown, ...args: unknown[]) {
        if (isNoise(args)) return;
        return target.apply(this, args);
      };
    };

    try {
      let currentError = wrapFn(window.console.error || (() => {}));
      Object.defineProperty(window.console, 'error', {
        configurable: true,
        enumerable: true,
        get: () => currentError,
        set: (fn) => {
          currentError = wrapFn(fn);
        },
      });
    } catch {}

    try {
      let currentWarn = wrapFn(window.console.warn || (() => {}));
      Object.defineProperty(window.console, 'warn', {
        configurable: true,
        enumerable: true,
        get: () => currentWarn,
        set: (fn) => {
          currentWarn = wrapFn(fn);
        },
      });
    } catch {}
  }
}

// Execute immediately when module is imported
applyDOMGuard();

export function DOMGuard() {
  useEffect(() => {
    applyDOMGuard();

    const handleError = (event: ErrorEvent) => {
      if (
        event.message &&
        (event.message.includes('bis_skin_checked') ||
          event.message.includes('bis_') ||
          event.message.includes("Failed to execute 'removeChild' on 'Node'") ||
          event.message.includes("Failed to execute 'insertBefore' on 'Node'") ||
          event.message.includes('The node to be removed is not a child of this node'))
      ) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation?.();
      }
    };

    window.addEventListener('error', handleError);
    return () => {
      window.removeEventListener('error', handleError);
    };
  }, []);

  return null;
}
