declare module '../../../package.json' {
  const packageJson: {
    version: string;
    name: string;
    [key: string]: any;
  };
  export default packageJson;
}
