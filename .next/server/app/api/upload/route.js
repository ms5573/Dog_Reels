/*
 * ATTENTION: An "eval-source-map" devtool has been used.
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file with attached SourceMaps in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
(() => {
var exports = {};
exports.id = "app/api/upload/route";
exports.ids = ["app/api/upload/route"];
exports.modules = {

/***/ "(rsc)/./app/api/upload/route.ts":
/*!*********************************!*\
  !*** ./app/api/upload/route.ts ***!
  \*********************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   POST: () => (/* binding */ POST)\n/* harmony export */ });\n/* harmony import */ var next_server__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! next/server */ \"(rsc)/./node_modules/next/dist/api/server.js\");\n/* harmony import */ var uuid__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! uuid */ \"(rsc)/./node_modules/uuid/dist/esm/v4.js\");\n/* harmony import */ var fs__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! fs */ \"fs\");\n/* harmony import */ var fs__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(fs__WEBPACK_IMPORTED_MODULE_1__);\n/* harmony import */ var path__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! path */ \"path\");\n/* harmony import */ var path__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(path__WEBPACK_IMPORTED_MODULE_2__);\n/* harmony import */ var child_process__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! child_process */ \"child_process\");\n/* harmony import */ var child_process__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(child_process__WEBPACK_IMPORTED_MODULE_3__);\n/* harmony import */ var util__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! util */ \"util\");\n/* harmony import */ var util__WEBPACK_IMPORTED_MODULE_4___default = /*#__PURE__*/__webpack_require__.n(util__WEBPACK_IMPORTED_MODULE_4__);\n\n\n\n\n\n\nconst execPromise = util__WEBPACK_IMPORTED_MODULE_4___default().promisify(child_process__WEBPACK_IMPORTED_MODULE_3__.exec);\nasync function POST(request) {\n    try {\n        // Create Output directory if it doesn't exist\n        const outputDir = path__WEBPACK_IMPORTED_MODULE_2___default().join(process.cwd(), 'Output');\n        if (!fs__WEBPACK_IMPORTED_MODULE_1___default().existsSync(outputDir)) {\n            fs__WEBPACK_IMPORTED_MODULE_1___default().mkdirSync(outputDir, {\n                recursive: true\n            });\n        }\n        const formData = await request.formData();\n        const dogPhoto = formData.get('dogPhoto');\n        const message = formData.get('message');\n        if (!dogPhoto || !message) {\n            return next_server__WEBPACK_IMPORTED_MODULE_0__.NextResponse.json({\n                error: 'Missing required fields'\n            }, {\n                status: 400\n            });\n        }\n        // Generate a unique task ID\n        const taskId = (0,uuid__WEBPACK_IMPORTED_MODULE_5__[\"default\"])();\n        // Get file buffer\n        const bytes = await dogPhoto.arrayBuffer();\n        const buffer = Buffer.from(bytes);\n        // Save the image to a temporary location\n        const imageExt = dogPhoto.name.split('.').pop() || 'jpg';\n        const imagePath = path__WEBPACK_IMPORTED_MODULE_2___default().join(outputDir, `${taskId}.${imageExt}`);\n        fs__WEBPACK_IMPORTED_MODULE_1___default().writeFileSync(imagePath, buffer);\n        // Save message to a file\n        const messagePath = path__WEBPACK_IMPORTED_MODULE_2___default().join(outputDir, `${taskId}.txt`);\n        fs__WEBPACK_IMPORTED_MODULE_1___default().writeFileSync(messagePath, message);\n        // Create a task status file to track progress\n        const statusFile = path__WEBPACK_IMPORTED_MODULE_2___default().join(outputDir, `${taskId}_status.json`);\n        fs__WEBPACK_IMPORTED_MODULE_1___default().writeFileSync(statusFile, JSON.stringify({\n            status: 'PENDING',\n            stage: 'Uploading...',\n            created: new Date().toISOString()\n        }));\n        // Run the Python Chibi-Clip process asynchronously\n        // Use the birthday-dance action to create a birthday themed animation\n        try {\n            // Use conda run with the specific environment\n            execPromise(`conda run -n chibi_env python chibi_clip/chibi_clip.py \"${imagePath}\" --action \"birthday-dance\" --extended-duration 45 --verbose`).then(({ stdout, stderr })=>{\n                console.log('Chibi-Clip process completed');\n                console.log('Output:', stdout);\n                // Look for the local_video_path in the output\n                const videoPathMatch = stdout.match(/Local video path: (.*\\.mp4)/);\n                const videoPath = videoPathMatch ? videoPathMatch[1] : null;\n                if (videoPath && fs__WEBPACK_IMPORTED_MODULE_1___default().existsSync(videoPath)) {\n                    // Update the status file with the completed information\n                    fs__WEBPACK_IMPORTED_MODULE_1___default().writeFileSync(statusFile, JSON.stringify({\n                        status: 'COMPLETE',\n                        stage: 'Complete',\n                        result_url: `/api/result/${taskId}`,\n                        videoPath: videoPath,\n                        completed: new Date().toISOString()\n                    }));\n                } else {\n                    // Update the status file with error information\n                    fs__WEBPACK_IMPORTED_MODULE_1___default().writeFileSync(statusFile, JSON.stringify({\n                        status: 'FAILED',\n                        stage: 'Video generation failed',\n                        error: 'Could not find generated video',\n                        completed: new Date().toISOString()\n                    }));\n                }\n            }).catch((error)=>{\n                console.error('Error during Chibi-Clip processing:', error);\n                fs__WEBPACK_IMPORTED_MODULE_1___default().writeFileSync(statusFile, JSON.stringify({\n                    status: 'FAILED',\n                    stage: 'Processing failed',\n                    error: error.message,\n                    completed: new Date().toISOString()\n                }));\n            });\n            // Don't wait for the process to complete - return immediately\n            return next_server__WEBPACK_IMPORTED_MODULE_0__.NextResponse.json({\n                success: true,\n                task_id: taskId,\n                message: 'Upload successful, processing started'\n            });\n        } catch (error) {\n            console.error('Error starting Python process:', error);\n            return next_server__WEBPACK_IMPORTED_MODULE_0__.NextResponse.json({\n                error: 'Failed to start processing'\n            }, {\n                status: 500\n            });\n        }\n    } catch (error) {\n        console.error('Upload error:', error);\n        return next_server__WEBPACK_IMPORTED_MODULE_0__.NextResponse.json({\n            error: 'Failed to process upload'\n        }, {\n            status: 500\n        });\n    }\n}\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKHJzYykvLi9hcHAvYXBpL3VwbG9hZC9yb3V0ZS50cyIsIm1hcHBpbmdzIjoiOzs7Ozs7Ozs7Ozs7OztBQUF3RDtBQUNwQjtBQUNoQjtBQUNJO0FBQ2E7QUFDYjtBQUV4QixNQUFNTyxjQUFjRCxxREFBYyxDQUFDRCwrQ0FBSUE7QUFFaEMsZUFBZUksS0FBS0MsT0FBb0I7SUFDN0MsSUFBSTtRQUNGLDhDQUE4QztRQUM5QyxNQUFNQyxZQUFZUCxnREFBUyxDQUFDUyxRQUFRQyxHQUFHLElBQUk7UUFDM0MsSUFBSSxDQUFDWCxvREFBYSxDQUFDUSxZQUFZO1lBQzdCUixtREFBWSxDQUFDUSxXQUFXO2dCQUFFTSxXQUFXO1lBQUs7UUFDNUM7UUFFQSxNQUFNQyxXQUFXLE1BQU1SLFFBQVFRLFFBQVE7UUFDdkMsTUFBTUMsV0FBV0QsU0FBU0UsR0FBRyxDQUFDO1FBQzlCLE1BQU1DLFVBQVVILFNBQVNFLEdBQUcsQ0FBQztRQUU3QixJQUFJLENBQUNELFlBQVksQ0FBQ0UsU0FBUztZQUN6QixPQUFPckIscURBQVlBLENBQUNzQixJQUFJLENBQ3RCO2dCQUFFQyxPQUFPO1lBQTBCLEdBQ25DO2dCQUFFQyxRQUFRO1lBQUk7UUFFbEI7UUFFQSw0QkFBNEI7UUFDNUIsTUFBTUMsU0FBU3ZCLGdEQUFNQTtRQUVyQixrQkFBa0I7UUFDbEIsTUFBTXdCLFFBQVEsTUFBTVAsU0FBU1EsV0FBVztRQUN4QyxNQUFNQyxTQUFTQyxPQUFPQyxJQUFJLENBQUNKO1FBRTNCLHlDQUF5QztRQUN6QyxNQUFNSyxXQUFXWixTQUFTYSxJQUFJLENBQUNDLEtBQUssQ0FBQyxLQUFLQyxHQUFHLE1BQU07UUFDbkQsTUFBTUMsWUFBWS9CLGdEQUFTLENBQUNPLFdBQVcsR0FBR2MsT0FBTyxDQUFDLEVBQUVNLFVBQVU7UUFDOUQ1Qix1REFBZ0IsQ0FBQ2dDLFdBQVdQO1FBRTVCLHlCQUF5QjtRQUN6QixNQUFNUyxjQUFjakMsZ0RBQVMsQ0FBQ08sV0FBVyxHQUFHYyxPQUFPLElBQUksQ0FBQztRQUN4RHRCLHVEQUFnQixDQUFDa0MsYUFBYWhCO1FBRTlCLDhDQUE4QztRQUM5QyxNQUFNaUIsYUFBYWxDLGdEQUFTLENBQUNPLFdBQVcsR0FBR2MsT0FBTyxZQUFZLENBQUM7UUFDL0R0Qix1REFBZ0IsQ0FBQ21DLFlBQVlDLEtBQUtDLFNBQVMsQ0FBQztZQUMxQ2hCLFFBQVE7WUFDUmlCLE9BQU87WUFDUEMsU0FBUyxJQUFJQyxPQUFPQyxXQUFXO1FBQ2pDO1FBRUEsbURBQW1EO1FBQ25ELHNFQUFzRTtRQUN0RSxJQUFJO1lBQ0YsOENBQThDO1lBQzlDckMsWUFBWSxDQUFDLHdEQUF3RCxFQUFFNEIsVUFBVSw0REFBNEQsQ0FBQyxFQUMzSVUsSUFBSSxDQUFDLENBQUMsRUFBRUMsTUFBTSxFQUFFQyxNQUFNLEVBQUU7Z0JBQ3ZCQyxRQUFRQyxHQUFHLENBQUM7Z0JBQ1pELFFBQVFDLEdBQUcsQ0FBQyxXQUFXSDtnQkFFdkIsOENBQThDO2dCQUM5QyxNQUFNSSxpQkFBaUJKLE9BQU9LLEtBQUssQ0FBQztnQkFDcEMsTUFBTUMsWUFBWUYsaUJBQWlCQSxjQUFjLENBQUMsRUFBRSxHQUFHO2dCQUV2RCxJQUFJRSxhQUFhakQsb0RBQWEsQ0FBQ2lELFlBQVk7b0JBQ3pDLHdEQUF3RDtvQkFDeERqRCx1REFBZ0IsQ0FBQ21DLFlBQVlDLEtBQUtDLFNBQVMsQ0FBQzt3QkFDMUNoQixRQUFRO3dCQUNSaUIsT0FBTzt3QkFDUFksWUFBWSxDQUFDLFlBQVksRUFBRTVCLFFBQVE7d0JBQ25DMkIsV0FBV0E7d0JBQ1hFLFdBQVcsSUFBSVgsT0FBT0MsV0FBVztvQkFDbkM7Z0JBQ0YsT0FBTztvQkFDTCxnREFBZ0Q7b0JBQ2hEekMsdURBQWdCLENBQUNtQyxZQUFZQyxLQUFLQyxTQUFTLENBQUM7d0JBQzFDaEIsUUFBUTt3QkFDUmlCLE9BQU87d0JBQ1BsQixPQUFPO3dCQUNQK0IsV0FBVyxJQUFJWCxPQUFPQyxXQUFXO29CQUNuQztnQkFDRjtZQUNGLEdBQ0NXLEtBQUssQ0FBQyxDQUFDaEM7Z0JBQ055QixRQUFRekIsS0FBSyxDQUFDLHVDQUF1Q0E7Z0JBQ3JEcEIsdURBQWdCLENBQUNtQyxZQUFZQyxLQUFLQyxTQUFTLENBQUM7b0JBQzFDaEIsUUFBUTtvQkFDUmlCLE9BQU87b0JBQ1BsQixPQUFPQSxNQUFNRixPQUFPO29CQUNwQmlDLFdBQVcsSUFBSVgsT0FBT0MsV0FBVztnQkFDbkM7WUFDRjtZQUVGLDhEQUE4RDtZQUM5RCxPQUFPNUMscURBQVlBLENBQUNzQixJQUFJLENBQUM7Z0JBQ3ZCa0MsU0FBUztnQkFDVEMsU0FBU2hDO2dCQUNUSixTQUFTO1lBQ1g7UUFDRixFQUFFLE9BQU9FLE9BQU87WUFDZHlCLFFBQVF6QixLQUFLLENBQUMsa0NBQWtDQTtZQUNoRCxPQUFPdkIscURBQVlBLENBQUNzQixJQUFJLENBQ3RCO2dCQUFFQyxPQUFPO1lBQTZCLEdBQ3RDO2dCQUFFQyxRQUFRO1lBQUk7UUFFbEI7SUFDRixFQUFFLE9BQU9ELE9BQU87UUFDZHlCLFFBQVF6QixLQUFLLENBQUMsaUJBQWlCQTtRQUMvQixPQUFPdkIscURBQVlBLENBQUNzQixJQUFJLENBQ3RCO1lBQUVDLE9BQU87UUFBMkIsR0FDcEM7WUFBRUMsUUFBUTtRQUFJO0lBRWxCO0FBQ0YiLCJzb3VyY2VzIjpbIi9Vc2Vycy9tYXJjc21pdGgvRGVza3RvcC9Qcm9qZWN0cy9Eb2cgUmVlbHMvYXBwL2FwaS91cGxvYWQvcm91dGUudHMiXSwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0IHsgTmV4dFJlcXVlc3QsIE5leHRSZXNwb25zZSB9IGZyb20gJ25leHQvc2VydmVyJztcbmltcG9ydCB7IHY0IGFzIHV1aWR2NCB9IGZyb20gJ3V1aWQnO1xuaW1wb3J0IGZzIGZyb20gJ2ZzJztcbmltcG9ydCBwYXRoIGZyb20gJ3BhdGgnO1xuaW1wb3J0IHsgZXhlYyB9IGZyb20gJ2NoaWxkX3Byb2Nlc3MnO1xuaW1wb3J0IHV0aWwgZnJvbSAndXRpbCc7XG5cbmNvbnN0IGV4ZWNQcm9taXNlID0gdXRpbC5wcm9taXNpZnkoZXhlYyk7XG5cbmV4cG9ydCBhc3luYyBmdW5jdGlvbiBQT1NUKHJlcXVlc3Q6IE5leHRSZXF1ZXN0KSB7XG4gIHRyeSB7XG4gICAgLy8gQ3JlYXRlIE91dHB1dCBkaXJlY3RvcnkgaWYgaXQgZG9lc24ndCBleGlzdFxuICAgIGNvbnN0IG91dHB1dERpciA9IHBhdGguam9pbihwcm9jZXNzLmN3ZCgpLCAnT3V0cHV0Jyk7XG4gICAgaWYgKCFmcy5leGlzdHNTeW5jKG91dHB1dERpcikpIHtcbiAgICAgIGZzLm1rZGlyU3luYyhvdXRwdXREaXIsIHsgcmVjdXJzaXZlOiB0cnVlIH0pO1xuICAgIH1cblxuICAgIGNvbnN0IGZvcm1EYXRhID0gYXdhaXQgcmVxdWVzdC5mb3JtRGF0YSgpO1xuICAgIGNvbnN0IGRvZ1Bob3RvID0gZm9ybURhdGEuZ2V0KCdkb2dQaG90bycpIGFzIEZpbGU7XG4gICAgY29uc3QgbWVzc2FnZSA9IGZvcm1EYXRhLmdldCgnbWVzc2FnZScpIGFzIHN0cmluZztcblxuICAgIGlmICghZG9nUGhvdG8gfHwgIW1lc3NhZ2UpIHtcbiAgICAgIHJldHVybiBOZXh0UmVzcG9uc2UuanNvbihcbiAgICAgICAgeyBlcnJvcjogJ01pc3NpbmcgcmVxdWlyZWQgZmllbGRzJyB9LFxuICAgICAgICB7IHN0YXR1czogNDAwIH1cbiAgICAgICk7XG4gICAgfVxuXG4gICAgLy8gR2VuZXJhdGUgYSB1bmlxdWUgdGFzayBJRFxuICAgIGNvbnN0IHRhc2tJZCA9IHV1aWR2NCgpO1xuICAgIFxuICAgIC8vIEdldCBmaWxlIGJ1ZmZlclxuICAgIGNvbnN0IGJ5dGVzID0gYXdhaXQgZG9nUGhvdG8uYXJyYXlCdWZmZXIoKTtcbiAgICBjb25zdCBidWZmZXIgPSBCdWZmZXIuZnJvbShieXRlcyk7XG5cbiAgICAvLyBTYXZlIHRoZSBpbWFnZSB0byBhIHRlbXBvcmFyeSBsb2NhdGlvblxuICAgIGNvbnN0IGltYWdlRXh0ID0gZG9nUGhvdG8ubmFtZS5zcGxpdCgnLicpLnBvcCgpIHx8ICdqcGcnO1xuICAgIGNvbnN0IGltYWdlUGF0aCA9IHBhdGguam9pbihvdXRwdXREaXIsIGAke3Rhc2tJZH0uJHtpbWFnZUV4dH1gKTtcbiAgICBmcy53cml0ZUZpbGVTeW5jKGltYWdlUGF0aCwgYnVmZmVyKTtcblxuICAgIC8vIFNhdmUgbWVzc2FnZSB0byBhIGZpbGVcbiAgICBjb25zdCBtZXNzYWdlUGF0aCA9IHBhdGguam9pbihvdXRwdXREaXIsIGAke3Rhc2tJZH0udHh0YCk7XG4gICAgZnMud3JpdGVGaWxlU3luYyhtZXNzYWdlUGF0aCwgbWVzc2FnZSk7XG5cbiAgICAvLyBDcmVhdGUgYSB0YXNrIHN0YXR1cyBmaWxlIHRvIHRyYWNrIHByb2dyZXNzXG4gICAgY29uc3Qgc3RhdHVzRmlsZSA9IHBhdGguam9pbihvdXRwdXREaXIsIGAke3Rhc2tJZH1fc3RhdHVzLmpzb25gKTtcbiAgICBmcy53cml0ZUZpbGVTeW5jKHN0YXR1c0ZpbGUsIEpTT04uc3RyaW5naWZ5KHtcbiAgICAgIHN0YXR1czogJ1BFTkRJTkcnLFxuICAgICAgc3RhZ2U6ICdVcGxvYWRpbmcuLi4nLFxuICAgICAgY3JlYXRlZDogbmV3IERhdGUoKS50b0lTT1N0cmluZygpXG4gICAgfSkpO1xuXG4gICAgLy8gUnVuIHRoZSBQeXRob24gQ2hpYmktQ2xpcCBwcm9jZXNzIGFzeW5jaHJvbm91c2x5XG4gICAgLy8gVXNlIHRoZSBiaXJ0aGRheS1kYW5jZSBhY3Rpb24gdG8gY3JlYXRlIGEgYmlydGhkYXkgdGhlbWVkIGFuaW1hdGlvblxuICAgIHRyeSB7XG4gICAgICAvLyBVc2UgY29uZGEgcnVuIHdpdGggdGhlIHNwZWNpZmljIGVudmlyb25tZW50XG4gICAgICBleGVjUHJvbWlzZShgY29uZGEgcnVuIC1uIGNoaWJpX2VudiBweXRob24gY2hpYmlfY2xpcC9jaGliaV9jbGlwLnB5IFwiJHtpbWFnZVBhdGh9XCIgLS1hY3Rpb24gXCJiaXJ0aGRheS1kYW5jZVwiIC0tZXh0ZW5kZWQtZHVyYXRpb24gNDUgLS12ZXJib3NlYClcbiAgICAgICAgLnRoZW4oKHsgc3Rkb3V0LCBzdGRlcnIgfSkgPT4ge1xuICAgICAgICAgIGNvbnNvbGUubG9nKCdDaGliaS1DbGlwIHByb2Nlc3MgY29tcGxldGVkJyk7XG4gICAgICAgICAgY29uc29sZS5sb2coJ091dHB1dDonLCBzdGRvdXQpO1xuICAgICAgICAgIFxuICAgICAgICAgIC8vIExvb2sgZm9yIHRoZSBsb2NhbF92aWRlb19wYXRoIGluIHRoZSBvdXRwdXRcbiAgICAgICAgICBjb25zdCB2aWRlb1BhdGhNYXRjaCA9IHN0ZG91dC5tYXRjaCgvTG9jYWwgdmlkZW8gcGF0aDogKC4qXFwubXA0KS8pO1xuICAgICAgICAgIGNvbnN0IHZpZGVvUGF0aCA9IHZpZGVvUGF0aE1hdGNoID8gdmlkZW9QYXRoTWF0Y2hbMV0gOiBudWxsO1xuICAgICAgICAgIFxuICAgICAgICAgIGlmICh2aWRlb1BhdGggJiYgZnMuZXhpc3RzU3luYyh2aWRlb1BhdGgpKSB7XG4gICAgICAgICAgICAvLyBVcGRhdGUgdGhlIHN0YXR1cyBmaWxlIHdpdGggdGhlIGNvbXBsZXRlZCBpbmZvcm1hdGlvblxuICAgICAgICAgICAgZnMud3JpdGVGaWxlU3luYyhzdGF0dXNGaWxlLCBKU09OLnN0cmluZ2lmeSh7XG4gICAgICAgICAgICAgIHN0YXR1czogJ0NPTVBMRVRFJyxcbiAgICAgICAgICAgICAgc3RhZ2U6ICdDb21wbGV0ZScsXG4gICAgICAgICAgICAgIHJlc3VsdF91cmw6IGAvYXBpL3Jlc3VsdC8ke3Rhc2tJZH1gLFxuICAgICAgICAgICAgICB2aWRlb1BhdGg6IHZpZGVvUGF0aCxcbiAgICAgICAgICAgICAgY29tcGxldGVkOiBuZXcgRGF0ZSgpLnRvSVNPU3RyaW5nKClcbiAgICAgICAgICAgIH0pKTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgLy8gVXBkYXRlIHRoZSBzdGF0dXMgZmlsZSB3aXRoIGVycm9yIGluZm9ybWF0aW9uXG4gICAgICAgICAgICBmcy53cml0ZUZpbGVTeW5jKHN0YXR1c0ZpbGUsIEpTT04uc3RyaW5naWZ5KHtcbiAgICAgICAgICAgICAgc3RhdHVzOiAnRkFJTEVEJyxcbiAgICAgICAgICAgICAgc3RhZ2U6ICdWaWRlbyBnZW5lcmF0aW9uIGZhaWxlZCcsXG4gICAgICAgICAgICAgIGVycm9yOiAnQ291bGQgbm90IGZpbmQgZ2VuZXJhdGVkIHZpZGVvJyxcbiAgICAgICAgICAgICAgY29tcGxldGVkOiBuZXcgRGF0ZSgpLnRvSVNPU3RyaW5nKClcbiAgICAgICAgICAgIH0pKTtcbiAgICAgICAgICB9XG4gICAgICAgIH0pXG4gICAgICAgIC5jYXRjaCgoZXJyb3IpID0+IHtcbiAgICAgICAgICBjb25zb2xlLmVycm9yKCdFcnJvciBkdXJpbmcgQ2hpYmktQ2xpcCBwcm9jZXNzaW5nOicsIGVycm9yKTtcbiAgICAgICAgICBmcy53cml0ZUZpbGVTeW5jKHN0YXR1c0ZpbGUsIEpTT04uc3RyaW5naWZ5KHtcbiAgICAgICAgICAgIHN0YXR1czogJ0ZBSUxFRCcsXG4gICAgICAgICAgICBzdGFnZTogJ1Byb2Nlc3NpbmcgZmFpbGVkJyxcbiAgICAgICAgICAgIGVycm9yOiBlcnJvci5tZXNzYWdlLFxuICAgICAgICAgICAgY29tcGxldGVkOiBuZXcgRGF0ZSgpLnRvSVNPU3RyaW5nKClcbiAgICAgICAgICB9KSk7XG4gICAgICAgIH0pO1xuXG4gICAgICAvLyBEb24ndCB3YWl0IGZvciB0aGUgcHJvY2VzcyB0byBjb21wbGV0ZSAtIHJldHVybiBpbW1lZGlhdGVseVxuICAgICAgcmV0dXJuIE5leHRSZXNwb25zZS5qc29uKHtcbiAgICAgICAgc3VjY2VzczogdHJ1ZSxcbiAgICAgICAgdGFza19pZDogdGFza0lkLFxuICAgICAgICBtZXNzYWdlOiAnVXBsb2FkIHN1Y2Nlc3NmdWwsIHByb2Nlc3Npbmcgc3RhcnRlZCdcbiAgICAgIH0pO1xuICAgIH0gY2F0Y2ggKGVycm9yKSB7XG4gICAgICBjb25zb2xlLmVycm9yKCdFcnJvciBzdGFydGluZyBQeXRob24gcHJvY2VzczonLCBlcnJvcik7XG4gICAgICByZXR1cm4gTmV4dFJlc3BvbnNlLmpzb24oXG4gICAgICAgIHsgZXJyb3I6ICdGYWlsZWQgdG8gc3RhcnQgcHJvY2Vzc2luZycgfSxcbiAgICAgICAgeyBzdGF0dXM6IDUwMCB9XG4gICAgICApO1xuICAgIH1cbiAgfSBjYXRjaCAoZXJyb3IpIHtcbiAgICBjb25zb2xlLmVycm9yKCdVcGxvYWQgZXJyb3I6JywgZXJyb3IpO1xuICAgIHJldHVybiBOZXh0UmVzcG9uc2UuanNvbihcbiAgICAgIHsgZXJyb3I6ICdGYWlsZWQgdG8gcHJvY2VzcyB1cGxvYWQnIH0sXG4gICAgICB7IHN0YXR1czogNTAwIH1cbiAgICApO1xuICB9XG59ICJdLCJuYW1lcyI6WyJOZXh0UmVzcG9uc2UiLCJ2NCIsInV1aWR2NCIsImZzIiwicGF0aCIsImV4ZWMiLCJ1dGlsIiwiZXhlY1Byb21pc2UiLCJwcm9taXNpZnkiLCJQT1NUIiwicmVxdWVzdCIsIm91dHB1dERpciIsImpvaW4iLCJwcm9jZXNzIiwiY3dkIiwiZXhpc3RzU3luYyIsIm1rZGlyU3luYyIsInJlY3Vyc2l2ZSIsImZvcm1EYXRhIiwiZG9nUGhvdG8iLCJnZXQiLCJtZXNzYWdlIiwianNvbiIsImVycm9yIiwic3RhdHVzIiwidGFza0lkIiwiYnl0ZXMiLCJhcnJheUJ1ZmZlciIsImJ1ZmZlciIsIkJ1ZmZlciIsImZyb20iLCJpbWFnZUV4dCIsIm5hbWUiLCJzcGxpdCIsInBvcCIsImltYWdlUGF0aCIsIndyaXRlRmlsZVN5bmMiLCJtZXNzYWdlUGF0aCIsInN0YXR1c0ZpbGUiLCJKU09OIiwic3RyaW5naWZ5Iiwic3RhZ2UiLCJjcmVhdGVkIiwiRGF0ZSIsInRvSVNPU3RyaW5nIiwidGhlbiIsInN0ZG91dCIsInN0ZGVyciIsImNvbnNvbGUiLCJsb2ciLCJ2aWRlb1BhdGhNYXRjaCIsIm1hdGNoIiwidmlkZW9QYXRoIiwicmVzdWx0X3VybCIsImNvbXBsZXRlZCIsImNhdGNoIiwic3VjY2VzcyIsInRhc2tfaWQiXSwiaWdub3JlTGlzdCI6W10sInNvdXJjZVJvb3QiOiIifQ==\n//# sourceURL=webpack-internal:///(rsc)/./app/api/upload/route.ts\n");

/***/ }),

/***/ "(rsc)/./node_modules/next/dist/build/webpack/loaders/next-app-loader/index.js?name=app%2Fapi%2Fupload%2Froute&page=%2Fapi%2Fupload%2Froute&appPaths=&pagePath=private-next-app-dir%2Fapi%2Fupload%2Froute.ts&appDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels%2Fapp&pageExtensions=tsx&pageExtensions=ts&pageExtensions=jsx&pageExtensions=js&rootDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels&isDev=true&tsconfigPath=tsconfig.json&basePath=&assetPrefix=&nextConfigOutput=&preferredRegion=&middlewareConfig=e30%3D!":
/*!******************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************!*\
  !*** ./node_modules/next/dist/build/webpack/loaders/next-app-loader/index.js?name=app%2Fapi%2Fupload%2Froute&page=%2Fapi%2Fupload%2Froute&appPaths=&pagePath=private-next-app-dir%2Fapi%2Fupload%2Froute.ts&appDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels%2Fapp&pageExtensions=tsx&pageExtensions=ts&pageExtensions=jsx&pageExtensions=js&rootDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels&isDev=true&tsconfigPath=tsconfig.json&basePath=&assetPrefix=&nextConfigOutput=&preferredRegion=&middlewareConfig=e30%3D! ***!
  \******************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   patchFetch: () => (/* binding */ patchFetch),\n/* harmony export */   routeModule: () => (/* binding */ routeModule),\n/* harmony export */   serverHooks: () => (/* binding */ serverHooks),\n/* harmony export */   workAsyncStorage: () => (/* binding */ workAsyncStorage),\n/* harmony export */   workUnitAsyncStorage: () => (/* binding */ workUnitAsyncStorage)\n/* harmony export */ });\n/* harmony import */ var next_dist_server_route_modules_app_route_module_compiled__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! next/dist/server/route-modules/app-route/module.compiled */ \"(rsc)/./node_modules/next/dist/server/route-modules/app-route/module.compiled.js\");\n/* harmony import */ var next_dist_server_route_modules_app_route_module_compiled__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(next_dist_server_route_modules_app_route_module_compiled__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var next_dist_server_route_kind__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! next/dist/server/route-kind */ \"(rsc)/./node_modules/next/dist/server/route-kind.js\");\n/* harmony import */ var next_dist_server_lib_patch_fetch__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! next/dist/server/lib/patch-fetch */ \"(rsc)/./node_modules/next/dist/server/lib/patch-fetch.js\");\n/* harmony import */ var next_dist_server_lib_patch_fetch__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(next_dist_server_lib_patch_fetch__WEBPACK_IMPORTED_MODULE_2__);\n/* harmony import */ var _Users_marcsmith_Desktop_Projects_Dog_Reels_app_api_upload_route_ts__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./app/api/upload/route.ts */ \"(rsc)/./app/api/upload/route.ts\");\n\n\n\n\n// We inject the nextConfigOutput here so that we can use them in the route\n// module.\nconst nextConfigOutput = \"\"\nconst routeModule = new next_dist_server_route_modules_app_route_module_compiled__WEBPACK_IMPORTED_MODULE_0__.AppRouteRouteModule({\n    definition: {\n        kind: next_dist_server_route_kind__WEBPACK_IMPORTED_MODULE_1__.RouteKind.APP_ROUTE,\n        page: \"/api/upload/route\",\n        pathname: \"/api/upload\",\n        filename: \"route\",\n        bundlePath: \"app/api/upload/route\"\n    },\n    resolvedPagePath: \"/Users/marcsmith/Desktop/Projects/Dog Reels/app/api/upload/route.ts\",\n    nextConfigOutput,\n    userland: _Users_marcsmith_Desktop_Projects_Dog_Reels_app_api_upload_route_ts__WEBPACK_IMPORTED_MODULE_3__\n});\n// Pull out the exports that we need to expose from the module. This should\n// be eliminated when we've moved the other routes to the new format. These\n// are used to hook into the route.\nconst { workAsyncStorage, workUnitAsyncStorage, serverHooks } = routeModule;\nfunction patchFetch() {\n    return (0,next_dist_server_lib_patch_fetch__WEBPACK_IMPORTED_MODULE_2__.patchFetch)({\n        workAsyncStorage,\n        workUnitAsyncStorage\n    });\n}\n\n\n//# sourceMappingURL=app-route.js.map//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKHJzYykvLi9ub2RlX21vZHVsZXMvbmV4dC9kaXN0L2J1aWxkL3dlYnBhY2svbG9hZGVycy9uZXh0LWFwcC1sb2FkZXIvaW5kZXguanM/bmFtZT1hcHAlMkZhcGklMkZ1cGxvYWQlMkZyb3V0ZSZwYWdlPSUyRmFwaSUyRnVwbG9hZCUyRnJvdXRlJmFwcFBhdGhzPSZwYWdlUGF0aD1wcml2YXRlLW5leHQtYXBwLWRpciUyRmFwaSUyRnVwbG9hZCUyRnJvdXRlLnRzJmFwcERpcj0lMkZVc2VycyUyRm1hcmNzbWl0aCUyRkRlc2t0b3AlMkZQcm9qZWN0cyUyRkRvZyUyMFJlZWxzJTJGYXBwJnBhZ2VFeHRlbnNpb25zPXRzeCZwYWdlRXh0ZW5zaW9ucz10cyZwYWdlRXh0ZW5zaW9ucz1qc3gmcGFnZUV4dGVuc2lvbnM9anMmcm9vdERpcj0lMkZVc2VycyUyRm1hcmNzbWl0aCUyRkRlc2t0b3AlMkZQcm9qZWN0cyUyRkRvZyUyMFJlZWxzJmlzRGV2PXRydWUmdHNjb25maWdQYXRoPXRzY29uZmlnLmpzb24mYmFzZVBhdGg9JmFzc2V0UHJlZml4PSZuZXh0Q29uZmlnT3V0cHV0PSZwcmVmZXJyZWRSZWdpb249Jm1pZGRsZXdhcmVDb25maWc9ZTMwJTNEISIsIm1hcHBpbmdzIjoiOzs7Ozs7Ozs7Ozs7OztBQUErRjtBQUN2QztBQUNxQjtBQUNtQjtBQUNoRztBQUNBO0FBQ0E7QUFDQSx3QkFBd0IseUdBQW1CO0FBQzNDO0FBQ0EsY0FBYyxrRUFBUztBQUN2QjtBQUNBO0FBQ0E7QUFDQTtBQUNBLEtBQUs7QUFDTDtBQUNBO0FBQ0EsWUFBWTtBQUNaLENBQUM7QUFDRDtBQUNBO0FBQ0E7QUFDQSxRQUFRLHNEQUFzRDtBQUM5RDtBQUNBLFdBQVcsNEVBQVc7QUFDdEI7QUFDQTtBQUNBLEtBQUs7QUFDTDtBQUMwRjs7QUFFMUYiLCJzb3VyY2VzIjpbIiJdLCJzb3VyY2VzQ29udGVudCI6WyJpbXBvcnQgeyBBcHBSb3V0ZVJvdXRlTW9kdWxlIH0gZnJvbSBcIm5leHQvZGlzdC9zZXJ2ZXIvcm91dGUtbW9kdWxlcy9hcHAtcm91dGUvbW9kdWxlLmNvbXBpbGVkXCI7XG5pbXBvcnQgeyBSb3V0ZUtpbmQgfSBmcm9tIFwibmV4dC9kaXN0L3NlcnZlci9yb3V0ZS1raW5kXCI7XG5pbXBvcnQgeyBwYXRjaEZldGNoIGFzIF9wYXRjaEZldGNoIH0gZnJvbSBcIm5leHQvZGlzdC9zZXJ2ZXIvbGliL3BhdGNoLWZldGNoXCI7XG5pbXBvcnQgKiBhcyB1c2VybGFuZCBmcm9tIFwiL1VzZXJzL21hcmNzbWl0aC9EZXNrdG9wL1Byb2plY3RzL0RvZyBSZWVscy9hcHAvYXBpL3VwbG9hZC9yb3V0ZS50c1wiO1xuLy8gV2UgaW5qZWN0IHRoZSBuZXh0Q29uZmlnT3V0cHV0IGhlcmUgc28gdGhhdCB3ZSBjYW4gdXNlIHRoZW0gaW4gdGhlIHJvdXRlXG4vLyBtb2R1bGUuXG5jb25zdCBuZXh0Q29uZmlnT3V0cHV0ID0gXCJcIlxuY29uc3Qgcm91dGVNb2R1bGUgPSBuZXcgQXBwUm91dGVSb3V0ZU1vZHVsZSh7XG4gICAgZGVmaW5pdGlvbjoge1xuICAgICAgICBraW5kOiBSb3V0ZUtpbmQuQVBQX1JPVVRFLFxuICAgICAgICBwYWdlOiBcIi9hcGkvdXBsb2FkL3JvdXRlXCIsXG4gICAgICAgIHBhdGhuYW1lOiBcIi9hcGkvdXBsb2FkXCIsXG4gICAgICAgIGZpbGVuYW1lOiBcInJvdXRlXCIsXG4gICAgICAgIGJ1bmRsZVBhdGg6IFwiYXBwL2FwaS91cGxvYWQvcm91dGVcIlxuICAgIH0sXG4gICAgcmVzb2x2ZWRQYWdlUGF0aDogXCIvVXNlcnMvbWFyY3NtaXRoL0Rlc2t0b3AvUHJvamVjdHMvRG9nIFJlZWxzL2FwcC9hcGkvdXBsb2FkL3JvdXRlLnRzXCIsXG4gICAgbmV4dENvbmZpZ091dHB1dCxcbiAgICB1c2VybGFuZFxufSk7XG4vLyBQdWxsIG91dCB0aGUgZXhwb3J0cyB0aGF0IHdlIG5lZWQgdG8gZXhwb3NlIGZyb20gdGhlIG1vZHVsZS4gVGhpcyBzaG91bGRcbi8vIGJlIGVsaW1pbmF0ZWQgd2hlbiB3ZSd2ZSBtb3ZlZCB0aGUgb3RoZXIgcm91dGVzIHRvIHRoZSBuZXcgZm9ybWF0LiBUaGVzZVxuLy8gYXJlIHVzZWQgdG8gaG9vayBpbnRvIHRoZSByb3V0ZS5cbmNvbnN0IHsgd29ya0FzeW5jU3RvcmFnZSwgd29ya1VuaXRBc3luY1N0b3JhZ2UsIHNlcnZlckhvb2tzIH0gPSByb3V0ZU1vZHVsZTtcbmZ1bmN0aW9uIHBhdGNoRmV0Y2goKSB7XG4gICAgcmV0dXJuIF9wYXRjaEZldGNoKHtcbiAgICAgICAgd29ya0FzeW5jU3RvcmFnZSxcbiAgICAgICAgd29ya1VuaXRBc3luY1N0b3JhZ2VcbiAgICB9KTtcbn1cbmV4cG9ydCB7IHJvdXRlTW9kdWxlLCB3b3JrQXN5bmNTdG9yYWdlLCB3b3JrVW5pdEFzeW5jU3RvcmFnZSwgc2VydmVySG9va3MsIHBhdGNoRmV0Y2gsICB9O1xuXG4vLyMgc291cmNlTWFwcGluZ1VSTD1hcHAtcm91dGUuanMubWFwIl0sIm5hbWVzIjpbXSwiaWdub3JlTGlzdCI6W10sInNvdXJjZVJvb3QiOiIifQ==\n//# sourceURL=webpack-internal:///(rsc)/./node_modules/next/dist/build/webpack/loaders/next-app-loader/index.js?name=app%2Fapi%2Fupload%2Froute&page=%2Fapi%2Fupload%2Froute&appPaths=&pagePath=private-next-app-dir%2Fapi%2Fupload%2Froute.ts&appDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels%2Fapp&pageExtensions=tsx&pageExtensions=ts&pageExtensions=jsx&pageExtensions=js&rootDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels&isDev=true&tsconfigPath=tsconfig.json&basePath=&assetPrefix=&nextConfigOutput=&preferredRegion=&middlewareConfig=e30%3D!\n");

/***/ }),

/***/ "(rsc)/./node_modules/next/dist/build/webpack/loaders/next-flight-client-entry-loader.js?server=true!":
/*!******************************************************************************************************!*\
  !*** ./node_modules/next/dist/build/webpack/loaders/next-flight-client-entry-loader.js?server=true! ***!
  \******************************************************************************************************/
/***/ (() => {



/***/ }),

/***/ "(ssr)/./node_modules/next/dist/build/webpack/loaders/next-flight-client-entry-loader.js?server=true!":
/*!******************************************************************************************************!*\
  !*** ./node_modules/next/dist/build/webpack/loaders/next-flight-client-entry-loader.js?server=true! ***!
  \******************************************************************************************************/
/***/ (() => {



/***/ }),

/***/ "../app-render/after-task-async-storage.external":
/*!***********************************************************************************!*\
  !*** external "next/dist/server/app-render/after-task-async-storage.external.js" ***!
  \***********************************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("next/dist/server/app-render/after-task-async-storage.external.js");

/***/ }),

/***/ "../app-render/work-async-storage.external":
/*!*****************************************************************************!*\
  !*** external "next/dist/server/app-render/work-async-storage.external.js" ***!
  \*****************************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("next/dist/server/app-render/work-async-storage.external.js");

/***/ }),

/***/ "./work-unit-async-storage.external":
/*!**********************************************************************************!*\
  !*** external "next/dist/server/app-render/work-unit-async-storage.external.js" ***!
  \**********************************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("next/dist/server/app-render/work-unit-async-storage.external.js");

/***/ }),

/***/ "child_process":
/*!********************************!*\
  !*** external "child_process" ***!
  \********************************/
/***/ ((module) => {

"use strict";
module.exports = require("child_process");

/***/ }),

/***/ "crypto":
/*!*************************!*\
  !*** external "crypto" ***!
  \*************************/
/***/ ((module) => {

"use strict";
module.exports = require("crypto");

/***/ }),

/***/ "fs":
/*!*********************!*\
  !*** external "fs" ***!
  \*********************/
/***/ ((module) => {

"use strict";
module.exports = require("fs");

/***/ }),

/***/ "next/dist/compiled/next-server/app-page.runtime.dev.js":
/*!*************************************************************************!*\
  !*** external "next/dist/compiled/next-server/app-page.runtime.dev.js" ***!
  \*************************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("next/dist/compiled/next-server/app-page.runtime.dev.js");

/***/ }),

/***/ "next/dist/compiled/next-server/app-route.runtime.dev.js":
/*!**************************************************************************!*\
  !*** external "next/dist/compiled/next-server/app-route.runtime.dev.js" ***!
  \**************************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("next/dist/compiled/next-server/app-route.runtime.dev.js");

/***/ }),

/***/ "path":
/*!***********************!*\
  !*** external "path" ***!
  \***********************/
/***/ ((module) => {

"use strict";
module.exports = require("path");

/***/ }),

/***/ "util":
/*!***********************!*\
  !*** external "util" ***!
  \***********************/
/***/ ((module) => {

"use strict";
module.exports = require("util");

/***/ })

};
;

// load runtime
var __webpack_require__ = require("../../../webpack-runtime.js");
__webpack_require__.C(exports);
var __webpack_exec__ = (moduleId) => (__webpack_require__(__webpack_require__.s = moduleId))
var __webpack_exports__ = __webpack_require__.X(0, ["vendor-chunks/next","vendor-chunks/uuid"], () => (__webpack_exec__("(rsc)/./node_modules/next/dist/build/webpack/loaders/next-app-loader/index.js?name=app%2Fapi%2Fupload%2Froute&page=%2Fapi%2Fupload%2Froute&appPaths=&pagePath=private-next-app-dir%2Fapi%2Fupload%2Froute.ts&appDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels%2Fapp&pageExtensions=tsx&pageExtensions=ts&pageExtensions=jsx&pageExtensions=js&rootDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels&isDev=true&tsconfigPath=tsconfig.json&basePath=&assetPrefix=&nextConfigOutput=&preferredRegion=&middlewareConfig=e30%3D!")));
module.exports = __webpack_exports__;

})();