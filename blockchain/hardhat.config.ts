import { HardhatUserConfig } from "hardhat/config";

// 完全不載入任何有 Bug 的擴充套件，只保留最核心的設定
const config: HardhatUserConfig = {
  solidity: "0.8.20", // 配合 OpenZeppelin 的版本需求
};

export default config;