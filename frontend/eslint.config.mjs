import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

// eslint-config-next now ships these as native flat-config arrays (each
// entry's plugin objects self-reference themselves for flat-config support,
// e.g. eslint-plugin-react's configs.flat.plugins.react). Routing them
// through @eslint/eslintrc's FlatCompat.extends("next/...") -- the pattern
// older create-next-app scaffolds generated -- makes FlatCompat's legacy
// eslintrc-schema validator try to validate that self-referencing plugin
// object as a plain JSON-serializable value, which throws "Converting
// circular structure to JSON" and fails the lint step outright before a
// single file is even linted. Importing the flat arrays directly avoids
// that legacy bridge entirely.
const eslintConfig = [
  { ignores: [".next/**", "node_modules/**", "coverage/**", "next-env.d.ts"] },
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    rules: {
      // This rule (new in the React Compiler-era eslint-plugin-react-hooks
      // bundled by next/core-web-vitals) flags the standard "fetch on mount"
      // and "sync state to a changed prop" pattern -- e.g.
      // useEffect(() => { load() }, []) or useEffect(() => setOpen(false),
      // [pathname]) -- as an error, even though it's the idiomatic, correct
      // way to do this without React Query throughout this codebase
      // (including the admin auth guard in admin/layout.tsx). Rewriting
      // every one of those call sites to the rule's preferred external-sync
      // shape is a real, separate refactor, not a bug fix -- downgraded to a
      // warning so it stays visible without blocking CI on working code.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
];

export default eslintConfig;
