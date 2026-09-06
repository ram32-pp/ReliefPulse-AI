import type { Metadata, Viewport } from 'next';
import './globals.css';
import { I18nProvider } from '@/lib/i18n';
import { ServiceWorkerCleaner } from '@/components/ServiceWorkerCleaner';
import { DOMGuard } from '@/components/DOMGuard';
import { OfflineSyncBanner } from '@/components/ui/OfflineSyncBanner';

export const metadata: Metadata = {
  title: 'ReliefPulse AI',
  description: 'Voice-first disaster management platform',
  manifest: '/manifest.json',
};

export const viewport: Viewport = {
  themeColor: '#1B2A4A',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                if (typeof window === 'undefined') return;

                // 1. Rock-solid console.error and console.warn filtering for extension attribute mismatches
                function isExtensionHydrationNoise(args) {
                  for (var i = 0; i < args.length; i++) {
                    var a = args[i];
                    if (typeof a === 'string') {
                      if (a.indexOf('bis_skin_checked') !== -1 || a.indexOf('bis_') !== -1) return true;
                    } else if (a && typeof a === 'object') {
                      var str = (a.message || '') + ' ' + (a.stack || '') + ' ' + (a.name || '');
                      if (str.indexOf('bis_skin_checked') !== -1 || str.indexOf('bis_') !== -1) return true;
                    }
                  }
                  return false;
                }

                function wrapConsoleFn(origFn) {
                  return function() {
                    if (isExtensionHydrationNoise(arguments)) {
                      return;
                    }
                    return origFn.apply(this, arguments);
                  };
                }

                if (window.console) {
                  var activeErrorFn = wrapConsoleFn(window.console.error || function() {});
                  var activeWarnFn = wrapConsoleFn(window.console.warn || function() {});

                  try {
                    Object.defineProperty(window.console, 'error', {
                      configurable: true,
                      enumerable: true,
                      get: function() { return activeErrorFn; },
                      set: function(newFn) { activeErrorFn = wrapConsoleFn(newFn); }
                    });
                  } catch (e) {
                    window.console.error = activeErrorFn;
                  }

                  try {
                    Object.defineProperty(window.console, 'warn', {
                      configurable: true,
                      enumerable: true,
                      get: function() { return activeWarnFn; },
                      set: function(newFn) { activeWarnFn = wrapConsoleFn(newFn); }
                    });
                  } catch (e) {
                    window.console.warn = activeWarnFn;
                  }
                }

                // 2. Global error event capture
                window.addEventListener('error', function(event) {
                  if (event && event.message && (event.message.indexOf('bis_skin_checked') !== -1 || event.message.indexOf('bis_') !== -1)) {
                    event.stopImmediatePropagation();
                    event.preventDefault();
                  }
                }, true);

                // 3. Guard Node DOM manipulation against extension crashes
                if (typeof Node !== 'undefined' && Node.prototype) {
                  var origRemoveChild = Node.prototype.removeChild;
                  Node.prototype.removeChild = function(child) {
                    if (child.parentNode !== this) {
                      if (child.parentNode) {
                        return child.parentNode.removeChild(child);
                      }
                      return child;
                    }
                    return origRemoveChild.apply(this, arguments);
                  };
                  var origInsertBefore = Node.prototype.insertBefore;
                  Node.prototype.insertBefore = function(newNode, referenceNode) {
                    if (referenceNode && referenceNode.parentNode !== this) {
                      if (referenceNode.parentNode) {
                        return referenceNode.parentNode.insertBefore(newNode, referenceNode);
                      }
                      return this.appendChild(newNode);
                    }
                    return origInsertBefore.apply(this, arguments);
                  };
                  var origReplaceChild = Node.prototype.replaceChild;
                  Node.prototype.replaceChild = function(newChild, oldChild) {
                    if (oldChild.parentNode !== this) {
                      if (oldChild.parentNode) {
                        return oldChild.parentNode.replaceChild(newChild, oldChild);
                      }
                      return this.appendChild(newChild);
                    }
                    return origReplaceChild.apply(this, arguments);
                  };
                }

                // 4. Neutralize browser extension attribute mutations (Bitdefender bis_skin_checked)
                if (typeof Element !== 'undefined' && Element.prototype) {
                  var origSetAttribute = Element.prototype.setAttribute;
                  Element.prototype.setAttribute = function(name, value) {
                    if (typeof name === 'string' && (name === 'bis_skin_checked' || name.indexOf('bis_') === 0)) {
                      return;
                    }
                    return origSetAttribute.apply(this, arguments);
                  };
                  var origHasAttribute = Element.prototype.hasAttribute;
                  Element.prototype.hasAttribute = function(name) {
                    if (typeof name === 'string' && (name === 'bis_skin_checked' || name.indexOf('bis_') === 0)) {
                      return false;
                    }
                    return origHasAttribute.apply(this, arguments);
                  };
                  var origGetAttribute = Element.prototype.getAttribute;
                  Element.prototype.getAttribute = function(name) {
                    if (typeof name === 'string' && (name === 'bis_skin_checked' || name.indexOf('bis_') === 0)) {
                      return null;
                    }
                    return origGetAttribute.apply(this, arguments);
                  };
                }

                // 5. Active DOM sanitization via MutationObserver
                if (typeof MutationObserver !== 'undefined' && document.documentElement) {
                  try {
                    var observer = new MutationObserver(function(mutations) {
                      for (var i = 0; i < mutations.length; i++) {
                        var m = mutations[i];
                        if (m.type === 'attributes' && m.attributeName && m.attributeName.indexOf('bis_') === 0) {
                          m.target.removeAttribute(m.attributeName);
                        } else if (m.type === 'childList') {
                          for (var j = 0; j < m.addedNodes.length; j++) {
                            var n = m.addedNodes[j];
                            if (n && n.nodeType === 1) {
                              if (n.hasAttribute && n.hasAttribute('bis_skin_checked')) {
                                n.removeAttribute('bis_skin_checked');
                              }
                              if (n.querySelectorAll) {
                                var bis = n.querySelectorAll('[bis_skin_checked]');
                                for (var k = 0; k < bis.length; k++) {
                                  bis[k].removeAttribute('bis_skin_checked');
                                }
                              }
                            }
                          }
                        }
                      }
                    });
                    observer.observe(document.documentElement, {
                      attributes: true,
                      subtree: true,
                      childList: true,
                      attributeFilter: ['bis_skin_checked']
                    });
                  } catch (e) {}
                }
              })();
            `,
          }}
        />
        <link rel="apple-touch-icon" href="/icon-192x192.png" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&family=Noto+Nastaliq+Urdu:wght@400;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body
        suppressHydrationWarning
        className="bg-[#070b14] text-warm-white antialiased"
      >
        <DOMGuard />
        <ServiceWorkerCleaner />
        <I18nProvider>
          <OfflineSyncBanner />
          {children}
        </I18nProvider>
      </body>
    </html>
  );
}
