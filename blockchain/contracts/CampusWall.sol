// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract CampusWall {
    address public owner;
    uint256 public nextPostId = 1;

    // 儲存鏈上所有已註冊的短暫環簽公鑰（供前端抓取作為誘餌）
    bytes32[] public ringPublicKeys;
    
    // 防範重複發文：記錄已被使用的 Key Image
    mapping(bytes32 => bool) public usedKeyImages;

    event ConfessionPosted(uint256 indexed postId, uint256 indexed parentId, string message);
    event PublicKeyRegistered(bytes32 indexed pubKey);

    // 限制只有 Relayer (代付中心) 可以呼叫
    modifier onlyOwner() {
        require(msg.sender == owner, "Only Relayer can call this");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    // Task 2.2：由後端 Relayer 呼叫，將學生的短暫公鑰寫入鏈上
    function registerPublicKey(bytes32 pubKey) public onlyOwner {
        ringPublicKeys.push(pubKey);
        emit PublicKeyRegistered(pubKey);
    }

    // 取得當前合約中所有的公鑰（Task 3.2 前端抓取誘餌用）
    function getRingPublicKeys() public view returns (bytes32[] memory) {
        return ringPublicKeys;
    }

    // Task 3 預留的發文接口 (驗證環簽章後發文)
    function postMessageWithRing(string memory message, uint256 parentId, bytes32 keyImage) public onlyOwner {
        require(!usedKeyImages[keyImage], "Key Image already used! Anti-replay.");
        usedKeyImages[keyImage] = true;
        
        emit ConfessionPosted(nextPostId, parentId, message);
        nextPostId++;
    }
}