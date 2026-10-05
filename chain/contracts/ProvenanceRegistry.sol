// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
 
import "@openzeppelin/contracts/access/AccessControl.sol";
 
/// @title ProvenanceRegistry
/// @notice Anchors a content hash + a metadata pointer on-chain so that
///   authenticity can be verified independently of TrustGuard's own
///   database. The registry NEVER stores media bytes -- only a
///   cryptographic commitment to them (sha256 of the original file).
contract ProvenanceRegistry is AccessControl {
    bytes32 public constant REGISTRAR_ROLE = keccak256("REGISTRAR_ROLE");
 
    struct Record {
        address creator;
        uint64  registeredAt;
        string  metadataURI;  // off-chain pointer (IPFS/HTTPS)
        bool    exists;
    }
 
    // mediaHash (sha256 of original bytes) => Record
    mapping(bytes32 => Record) private _records;
 
    event MediaRegistered(
        bytes32 indexed mediaHash,
        address indexed creator,
        string metadataURI,
        uint64 registeredAt
    );
 
    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(REGISTRAR_ROLE, admin);
    }
 
    /// @notice Registers a new media hash. Reverts if already present --
    ///   registration is intentionally NOT idempotent on-chain; the
    ///   backend checks Postgres's uq_provenance_media_hash FIRST and
    ///   never submits a transaction it expects to revert (§6.1).
    function register(
        bytes32 mediaHash,
        address creator,
        string calldata metadataURI
    ) external onlyRole(REGISTRAR_ROLE) {
        require(!_records[mediaHash].exists, "ProvenanceRegistry: exists");
        _records[mediaHash] = Record({
            creator: creator,
            registeredAt: uint64(block.timestamp),
            metadataURI: metadataURI,
            exists: true
        });
        emit MediaRegistered(
            mediaHash, creator, metadataURI, uint64(block.timestamp)
        );
    }
 
    function verify(bytes32 mediaHash)
        external
        view
        returns (
            bool found,
            address creator,
            uint64 registeredAt,
            string memory metadataURI
        )
    {
        Record storage r = _records[mediaHash];
        return (r.exists, r.creator, r.registeredAt, r.metadataURI);
    }
}
