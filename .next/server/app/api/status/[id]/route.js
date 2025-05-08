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
exports.id = "app/api/status/[id]/route";
exports.ids = ["app/api/status/[id]/route"];
exports.modules = {

/***/ "(rsc)/./app/api/status/[id]/route.ts":
/*!**************************************!*\
  !*** ./app/api/status/[id]/route.ts ***!
  \**************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   GET: () => (/* binding */ GET)\n/* harmony export */ });\n/* harmony import */ var next_server__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! next/server */ \"(rsc)/./node_modules/next/dist/api/server.js\");\n/* harmony import */ var fs__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! fs */ \"fs\");\n/* harmony import */ var fs__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(fs__WEBPACK_IMPORTED_MODULE_1__);\n/* harmony import */ var path__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! path */ \"path\");\n/* harmony import */ var path__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(path__WEBPACK_IMPORTED_MODULE_2__);\n\n\n\nasync function GET(request, { params }) {\n    try {\n        // Make sure to await params for Next.js 15 compatibility\n        const { id } = params;\n        const taskId = id;\n        const outputDir = path__WEBPACK_IMPORTED_MODULE_2___default().join(process.cwd(), 'Output');\n        // Check if status file exists\n        const statusFile = path__WEBPACK_IMPORTED_MODULE_2___default().join(outputDir, `${taskId}_status.json`);\n        if (!fs__WEBPACK_IMPORTED_MODULE_1___default().existsSync(statusFile)) {\n            // Fall back to checking if task exists (by looking for task message file)\n            const messagePath = path__WEBPACK_IMPORTED_MODULE_2___default().join(outputDir, `${taskId}.txt`);\n            if (!fs__WEBPACK_IMPORTED_MODULE_1___default().existsSync(messagePath)) {\n                return next_server__WEBPACK_IMPORTED_MODULE_0__.NextResponse.json({\n                    error: 'Task not found'\n                }, {\n                    status: 404\n                });\n            }\n            // If message file exists but no status file, create a default status\n            return next_server__WEBPACK_IMPORTED_MODULE_0__.NextResponse.json({\n                status: 'PENDING',\n                stage: 'Initializing...',\n                message: 'Your request is being processed'\n            });\n        }\n        // Read the status file\n        const statusData = fs__WEBPACK_IMPORTED_MODULE_1___default().readFileSync(statusFile, 'utf8');\n        const status = JSON.parse(statusData);\n        return next_server__WEBPACK_IMPORTED_MODULE_0__.NextResponse.json(status);\n    } catch (error) {\n        console.error('Status check error:', error);\n        return next_server__WEBPACK_IMPORTED_MODULE_0__.NextResponse.json({\n            error: 'Failed to check status',\n            status: 'FAILED'\n        }, {\n            status: 500\n        });\n    }\n}\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKHJzYykvLi9hcHAvYXBpL3N0YXR1cy9baWRdL3JvdXRlLnRzIiwibWFwcGluZ3MiOiI7Ozs7Ozs7OztBQUF3RDtBQUNwQztBQUNJO0FBRWpCLGVBQWVHLElBQ3BCQyxPQUFvQixFQUNwQixFQUFFQyxNQUFNLEVBQThCO0lBRXRDLElBQUk7UUFDRix5REFBeUQ7UUFDekQsTUFBTSxFQUFFQyxFQUFFLEVBQUUsR0FBR0Q7UUFDZixNQUFNRSxTQUFTRDtRQUNmLE1BQU1FLFlBQVlOLGdEQUFTLENBQUNRLFFBQVFDLEdBQUcsSUFBSTtRQUUzQyw4QkFBOEI7UUFDOUIsTUFBTUMsYUFBYVYsZ0RBQVMsQ0FBQ00sV0FBVyxHQUFHRCxPQUFPLFlBQVksQ0FBQztRQUMvRCxJQUFJLENBQUNOLG9EQUFhLENBQUNXLGFBQWE7WUFDOUIsMEVBQTBFO1lBQzFFLE1BQU1FLGNBQWNaLGdEQUFTLENBQUNNLFdBQVcsR0FBR0QsT0FBTyxJQUFJLENBQUM7WUFDeEQsSUFBSSxDQUFDTixvREFBYSxDQUFDYSxjQUFjO2dCQUMvQixPQUFPZCxxREFBWUEsQ0FBQ2UsSUFBSSxDQUN0QjtvQkFBRUMsT0FBTztnQkFBaUIsR0FDMUI7b0JBQUVDLFFBQVE7Z0JBQUk7WUFFbEI7WUFFQSxxRUFBcUU7WUFDckUsT0FBT2pCLHFEQUFZQSxDQUFDZSxJQUFJLENBQUM7Z0JBQ3ZCRSxRQUFRO2dCQUNSQyxPQUFPO2dCQUNQQyxTQUFTO1lBQ1g7UUFDRjtRQUVBLHVCQUF1QjtRQUN2QixNQUFNQyxhQUFhbkIsc0RBQWUsQ0FBQ1csWUFBWTtRQUMvQyxNQUFNSyxTQUFTSyxLQUFLQyxLQUFLLENBQUNIO1FBRTFCLE9BQU9wQixxREFBWUEsQ0FBQ2UsSUFBSSxDQUFDRTtJQUMzQixFQUFFLE9BQU9ELE9BQU87UUFDZFEsUUFBUVIsS0FBSyxDQUFDLHVCQUF1QkE7UUFDckMsT0FBT2hCLHFEQUFZQSxDQUFDZSxJQUFJLENBQ3RCO1lBQUVDLE9BQU87WUFBMEJDLFFBQVE7UUFBUyxHQUNwRDtZQUFFQSxRQUFRO1FBQUk7SUFFbEI7QUFDRiIsInNvdXJjZXMiOlsiL1VzZXJzL21hcmNzbWl0aC9EZXNrdG9wL1Byb2plY3RzL0RvZyBSZWVscy9hcHAvYXBpL3N0YXR1cy9baWRdL3JvdXRlLnRzIl0sInNvdXJjZXNDb250ZW50IjpbImltcG9ydCB7IE5leHRSZXF1ZXN0LCBOZXh0UmVzcG9uc2UgfSBmcm9tICduZXh0L3NlcnZlcic7XG5pbXBvcnQgZnMgZnJvbSAnZnMnO1xuaW1wb3J0IHBhdGggZnJvbSAncGF0aCc7XG5cbmV4cG9ydCBhc3luYyBmdW5jdGlvbiBHRVQoXG4gIHJlcXVlc3Q6IE5leHRSZXF1ZXN0LFxuICB7IHBhcmFtcyB9OiB7IHBhcmFtczogeyBpZDogc3RyaW5nIH0gfVxuKSB7XG4gIHRyeSB7XG4gICAgLy8gTWFrZSBzdXJlIHRvIGF3YWl0IHBhcmFtcyBmb3IgTmV4dC5qcyAxNSBjb21wYXRpYmlsaXR5XG4gICAgY29uc3QgeyBpZCB9ID0gcGFyYW1zO1xuICAgIGNvbnN0IHRhc2tJZCA9IGlkO1xuICAgIGNvbnN0IG91dHB1dERpciA9IHBhdGguam9pbihwcm9jZXNzLmN3ZCgpLCAnT3V0cHV0Jyk7XG4gICAgXG4gICAgLy8gQ2hlY2sgaWYgc3RhdHVzIGZpbGUgZXhpc3RzXG4gICAgY29uc3Qgc3RhdHVzRmlsZSA9IHBhdGguam9pbihvdXRwdXREaXIsIGAke3Rhc2tJZH1fc3RhdHVzLmpzb25gKTtcbiAgICBpZiAoIWZzLmV4aXN0c1N5bmMoc3RhdHVzRmlsZSkpIHtcbiAgICAgIC8vIEZhbGwgYmFjayB0byBjaGVja2luZyBpZiB0YXNrIGV4aXN0cyAoYnkgbG9va2luZyBmb3IgdGFzayBtZXNzYWdlIGZpbGUpXG4gICAgICBjb25zdCBtZXNzYWdlUGF0aCA9IHBhdGguam9pbihvdXRwdXREaXIsIGAke3Rhc2tJZH0udHh0YCk7XG4gICAgICBpZiAoIWZzLmV4aXN0c1N5bmMobWVzc2FnZVBhdGgpKSB7XG4gICAgICAgIHJldHVybiBOZXh0UmVzcG9uc2UuanNvbihcbiAgICAgICAgICB7IGVycm9yOiAnVGFzayBub3QgZm91bmQnIH0sXG4gICAgICAgICAgeyBzdGF0dXM6IDQwNCB9XG4gICAgICAgICk7XG4gICAgICB9XG4gICAgICBcbiAgICAgIC8vIElmIG1lc3NhZ2UgZmlsZSBleGlzdHMgYnV0IG5vIHN0YXR1cyBmaWxlLCBjcmVhdGUgYSBkZWZhdWx0IHN0YXR1c1xuICAgICAgcmV0dXJuIE5leHRSZXNwb25zZS5qc29uKHtcbiAgICAgICAgc3RhdHVzOiAnUEVORElORycsXG4gICAgICAgIHN0YWdlOiAnSW5pdGlhbGl6aW5nLi4uJyxcbiAgICAgICAgbWVzc2FnZTogJ1lvdXIgcmVxdWVzdCBpcyBiZWluZyBwcm9jZXNzZWQnXG4gICAgICB9KTtcbiAgICB9XG4gICAgXG4gICAgLy8gUmVhZCB0aGUgc3RhdHVzIGZpbGVcbiAgICBjb25zdCBzdGF0dXNEYXRhID0gZnMucmVhZEZpbGVTeW5jKHN0YXR1c0ZpbGUsICd1dGY4Jyk7XG4gICAgY29uc3Qgc3RhdHVzID0gSlNPTi5wYXJzZShzdGF0dXNEYXRhKTtcbiAgICBcbiAgICByZXR1cm4gTmV4dFJlc3BvbnNlLmpzb24oc3RhdHVzKTtcbiAgfSBjYXRjaCAoZXJyb3IpIHtcbiAgICBjb25zb2xlLmVycm9yKCdTdGF0dXMgY2hlY2sgZXJyb3I6JywgZXJyb3IpO1xuICAgIHJldHVybiBOZXh0UmVzcG9uc2UuanNvbihcbiAgICAgIHsgZXJyb3I6ICdGYWlsZWQgdG8gY2hlY2sgc3RhdHVzJywgc3RhdHVzOiAnRkFJTEVEJyB9LFxuICAgICAgeyBzdGF0dXM6IDUwMCB9XG4gICAgKTtcbiAgfVxufSAiXSwibmFtZXMiOlsiTmV4dFJlc3BvbnNlIiwiZnMiLCJwYXRoIiwiR0VUIiwicmVxdWVzdCIsInBhcmFtcyIsImlkIiwidGFza0lkIiwib3V0cHV0RGlyIiwiam9pbiIsInByb2Nlc3MiLCJjd2QiLCJzdGF0dXNGaWxlIiwiZXhpc3RzU3luYyIsIm1lc3NhZ2VQYXRoIiwianNvbiIsImVycm9yIiwic3RhdHVzIiwic3RhZ2UiLCJtZXNzYWdlIiwic3RhdHVzRGF0YSIsInJlYWRGaWxlU3luYyIsIkpTT04iLCJwYXJzZSIsImNvbnNvbGUiXSwiaWdub3JlTGlzdCI6W10sInNvdXJjZVJvb3QiOiIifQ==\n//# sourceURL=webpack-internal:///(rsc)/./app/api/status/[id]/route.ts\n");

/***/ }),

/***/ "(rsc)/./node_modules/next/dist/build/webpack/loaders/next-app-loader/index.js?name=app%2Fapi%2Fstatus%2F%5Bid%5D%2Froute&page=%2Fapi%2Fstatus%2F%5Bid%5D%2Froute&appPaths=&pagePath=private-next-app-dir%2Fapi%2Fstatus%2F%5Bid%5D%2Froute.ts&appDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels%2Fapp&pageExtensions=tsx&pageExtensions=ts&pageExtensions=jsx&pageExtensions=js&rootDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels&isDev=true&tsconfigPath=tsconfig.json&basePath=&assetPrefix=&nextConfigOutput=&preferredRegion=&middlewareConfig=e30%3D!":
/*!***************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************!*\
  !*** ./node_modules/next/dist/build/webpack/loaders/next-app-loader/index.js?name=app%2Fapi%2Fstatus%2F%5Bid%5D%2Froute&page=%2Fapi%2Fstatus%2F%5Bid%5D%2Froute&appPaths=&pagePath=private-next-app-dir%2Fapi%2Fstatus%2F%5Bid%5D%2Froute.ts&appDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels%2Fapp&pageExtensions=tsx&pageExtensions=ts&pageExtensions=jsx&pageExtensions=js&rootDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels&isDev=true&tsconfigPath=tsconfig.json&basePath=&assetPrefix=&nextConfigOutput=&preferredRegion=&middlewareConfig=e30%3D! ***!
  \***************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   patchFetch: () => (/* binding */ patchFetch),\n/* harmony export */   routeModule: () => (/* binding */ routeModule),\n/* harmony export */   serverHooks: () => (/* binding */ serverHooks),\n/* harmony export */   workAsyncStorage: () => (/* binding */ workAsyncStorage),\n/* harmony export */   workUnitAsyncStorage: () => (/* binding */ workUnitAsyncStorage)\n/* harmony export */ });\n/* harmony import */ var next_dist_server_route_modules_app_route_module_compiled__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! next/dist/server/route-modules/app-route/module.compiled */ \"(rsc)/./node_modules/next/dist/server/route-modules/app-route/module.compiled.js\");\n/* harmony import */ var next_dist_server_route_modules_app_route_module_compiled__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(next_dist_server_route_modules_app_route_module_compiled__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var next_dist_server_route_kind__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! next/dist/server/route-kind */ \"(rsc)/./node_modules/next/dist/server/route-kind.js\");\n/* harmony import */ var next_dist_server_lib_patch_fetch__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! next/dist/server/lib/patch-fetch */ \"(rsc)/./node_modules/next/dist/server/lib/patch-fetch.js\");\n/* harmony import */ var next_dist_server_lib_patch_fetch__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(next_dist_server_lib_patch_fetch__WEBPACK_IMPORTED_MODULE_2__);\n/* harmony import */ var _Users_marcsmith_Desktop_Projects_Dog_Reels_app_api_status_id_route_ts__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./app/api/status/[id]/route.ts */ \"(rsc)/./app/api/status/[id]/route.ts\");\n\n\n\n\n// We inject the nextConfigOutput here so that we can use them in the route\n// module.\nconst nextConfigOutput = \"\"\nconst routeModule = new next_dist_server_route_modules_app_route_module_compiled__WEBPACK_IMPORTED_MODULE_0__.AppRouteRouteModule({\n    definition: {\n        kind: next_dist_server_route_kind__WEBPACK_IMPORTED_MODULE_1__.RouteKind.APP_ROUTE,\n        page: \"/api/status/[id]/route\",\n        pathname: \"/api/status/[id]\",\n        filename: \"route\",\n        bundlePath: \"app/api/status/[id]/route\"\n    },\n    resolvedPagePath: \"/Users/marcsmith/Desktop/Projects/Dog Reels/app/api/status/[id]/route.ts\",\n    nextConfigOutput,\n    userland: _Users_marcsmith_Desktop_Projects_Dog_Reels_app_api_status_id_route_ts__WEBPACK_IMPORTED_MODULE_3__\n});\n// Pull out the exports that we need to expose from the module. This should\n// be eliminated when we've moved the other routes to the new format. These\n// are used to hook into the route.\nconst { workAsyncStorage, workUnitAsyncStorage, serverHooks } = routeModule;\nfunction patchFetch() {\n    return (0,next_dist_server_lib_patch_fetch__WEBPACK_IMPORTED_MODULE_2__.patchFetch)({\n        workAsyncStorage,\n        workUnitAsyncStorage\n    });\n}\n\n\n//# sourceMappingURL=app-route.js.map//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKHJzYykvLi9ub2RlX21vZHVsZXMvbmV4dC9kaXN0L2J1aWxkL3dlYnBhY2svbG9hZGVycy9uZXh0LWFwcC1sb2FkZXIvaW5kZXguanM/bmFtZT1hcHAlMkZhcGklMkZzdGF0dXMlMkYlNUJpZCU1RCUyRnJvdXRlJnBhZ2U9JTJGYXBpJTJGc3RhdHVzJTJGJTVCaWQlNUQlMkZyb3V0ZSZhcHBQYXRocz0mcGFnZVBhdGg9cHJpdmF0ZS1uZXh0LWFwcC1kaXIlMkZhcGklMkZzdGF0dXMlMkYlNUJpZCU1RCUyRnJvdXRlLnRzJmFwcERpcj0lMkZVc2VycyUyRm1hcmNzbWl0aCUyRkRlc2t0b3AlMkZQcm9qZWN0cyUyRkRvZyUyMFJlZWxzJTJGYXBwJnBhZ2VFeHRlbnNpb25zPXRzeCZwYWdlRXh0ZW5zaW9ucz10cyZwYWdlRXh0ZW5zaW9ucz1qc3gmcGFnZUV4dGVuc2lvbnM9anMmcm9vdERpcj0lMkZVc2VycyUyRm1hcmNzbWl0aCUyRkRlc2t0b3AlMkZQcm9qZWN0cyUyRkRvZyUyMFJlZWxzJmlzRGV2PXRydWUmdHNjb25maWdQYXRoPXRzY29uZmlnLmpzb24mYmFzZVBhdGg9JmFzc2V0UHJlZml4PSZuZXh0Q29uZmlnT3V0cHV0PSZwcmVmZXJyZWRSZWdpb249Jm1pZGRsZXdhcmVDb25maWc9ZTMwJTNEISIsIm1hcHBpbmdzIjoiOzs7Ozs7Ozs7Ozs7OztBQUErRjtBQUN2QztBQUNxQjtBQUN3QjtBQUNyRztBQUNBO0FBQ0E7QUFDQSx3QkFBd0IseUdBQW1CO0FBQzNDO0FBQ0EsY0FBYyxrRUFBUztBQUN2QjtBQUNBO0FBQ0E7QUFDQTtBQUNBLEtBQUs7QUFDTDtBQUNBO0FBQ0EsWUFBWTtBQUNaLENBQUM7QUFDRDtBQUNBO0FBQ0E7QUFDQSxRQUFRLHNEQUFzRDtBQUM5RDtBQUNBLFdBQVcsNEVBQVc7QUFDdEI7QUFDQTtBQUNBLEtBQUs7QUFDTDtBQUMwRjs7QUFFMUYiLCJzb3VyY2VzIjpbIiJdLCJzb3VyY2VzQ29udGVudCI6WyJpbXBvcnQgeyBBcHBSb3V0ZVJvdXRlTW9kdWxlIH0gZnJvbSBcIm5leHQvZGlzdC9zZXJ2ZXIvcm91dGUtbW9kdWxlcy9hcHAtcm91dGUvbW9kdWxlLmNvbXBpbGVkXCI7XG5pbXBvcnQgeyBSb3V0ZUtpbmQgfSBmcm9tIFwibmV4dC9kaXN0L3NlcnZlci9yb3V0ZS1raW5kXCI7XG5pbXBvcnQgeyBwYXRjaEZldGNoIGFzIF9wYXRjaEZldGNoIH0gZnJvbSBcIm5leHQvZGlzdC9zZXJ2ZXIvbGliL3BhdGNoLWZldGNoXCI7XG5pbXBvcnQgKiBhcyB1c2VybGFuZCBmcm9tIFwiL1VzZXJzL21hcmNzbWl0aC9EZXNrdG9wL1Byb2plY3RzL0RvZyBSZWVscy9hcHAvYXBpL3N0YXR1cy9baWRdL3JvdXRlLnRzXCI7XG4vLyBXZSBpbmplY3QgdGhlIG5leHRDb25maWdPdXRwdXQgaGVyZSBzbyB0aGF0IHdlIGNhbiB1c2UgdGhlbSBpbiB0aGUgcm91dGVcbi8vIG1vZHVsZS5cbmNvbnN0IG5leHRDb25maWdPdXRwdXQgPSBcIlwiXG5jb25zdCByb3V0ZU1vZHVsZSA9IG5ldyBBcHBSb3V0ZVJvdXRlTW9kdWxlKHtcbiAgICBkZWZpbml0aW9uOiB7XG4gICAgICAgIGtpbmQ6IFJvdXRlS2luZC5BUFBfUk9VVEUsXG4gICAgICAgIHBhZ2U6IFwiL2FwaS9zdGF0dXMvW2lkXS9yb3V0ZVwiLFxuICAgICAgICBwYXRobmFtZTogXCIvYXBpL3N0YXR1cy9baWRdXCIsXG4gICAgICAgIGZpbGVuYW1lOiBcInJvdXRlXCIsXG4gICAgICAgIGJ1bmRsZVBhdGg6IFwiYXBwL2FwaS9zdGF0dXMvW2lkXS9yb3V0ZVwiXG4gICAgfSxcbiAgICByZXNvbHZlZFBhZ2VQYXRoOiBcIi9Vc2Vycy9tYXJjc21pdGgvRGVza3RvcC9Qcm9qZWN0cy9Eb2cgUmVlbHMvYXBwL2FwaS9zdGF0dXMvW2lkXS9yb3V0ZS50c1wiLFxuICAgIG5leHRDb25maWdPdXRwdXQsXG4gICAgdXNlcmxhbmRcbn0pO1xuLy8gUHVsbCBvdXQgdGhlIGV4cG9ydHMgdGhhdCB3ZSBuZWVkIHRvIGV4cG9zZSBmcm9tIHRoZSBtb2R1bGUuIFRoaXMgc2hvdWxkXG4vLyBiZSBlbGltaW5hdGVkIHdoZW4gd2UndmUgbW92ZWQgdGhlIG90aGVyIHJvdXRlcyB0byB0aGUgbmV3IGZvcm1hdC4gVGhlc2Vcbi8vIGFyZSB1c2VkIHRvIGhvb2sgaW50byB0aGUgcm91dGUuXG5jb25zdCB7IHdvcmtBc3luY1N0b3JhZ2UsIHdvcmtVbml0QXN5bmNTdG9yYWdlLCBzZXJ2ZXJIb29rcyB9ID0gcm91dGVNb2R1bGU7XG5mdW5jdGlvbiBwYXRjaEZldGNoKCkge1xuICAgIHJldHVybiBfcGF0Y2hGZXRjaCh7XG4gICAgICAgIHdvcmtBc3luY1N0b3JhZ2UsXG4gICAgICAgIHdvcmtVbml0QXN5bmNTdG9yYWdlXG4gICAgfSk7XG59XG5leHBvcnQgeyByb3V0ZU1vZHVsZSwgd29ya0FzeW5jU3RvcmFnZSwgd29ya1VuaXRBc3luY1N0b3JhZ2UsIHNlcnZlckhvb2tzLCBwYXRjaEZldGNoLCAgfTtcblxuLy8jIHNvdXJjZU1hcHBpbmdVUkw9YXBwLXJvdXRlLmpzLm1hcCJdLCJuYW1lcyI6W10sImlnbm9yZUxpc3QiOltdLCJzb3VyY2VSb290IjoiIn0=\n//# sourceURL=webpack-internal:///(rsc)/./node_modules/next/dist/build/webpack/loaders/next-app-loader/index.js?name=app%2Fapi%2Fstatus%2F%5Bid%5D%2Froute&page=%2Fapi%2Fstatus%2F%5Bid%5D%2Froute&appPaths=&pagePath=private-next-app-dir%2Fapi%2Fstatus%2F%5Bid%5D%2Froute.ts&appDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels%2Fapp&pageExtensions=tsx&pageExtensions=ts&pageExtensions=jsx&pageExtensions=js&rootDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels&isDev=true&tsconfigPath=tsconfig.json&basePath=&assetPrefix=&nextConfigOutput=&preferredRegion=&middlewareConfig=e30%3D!\n");

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

/***/ })

};
;

// load runtime
var __webpack_require__ = require("../../../../webpack-runtime.js");
__webpack_require__.C(exports);
var __webpack_exec__ = (moduleId) => (__webpack_require__(__webpack_require__.s = moduleId))
var __webpack_exports__ = __webpack_require__.X(0, ["vendor-chunks/next"], () => (__webpack_exec__("(rsc)/./node_modules/next/dist/build/webpack/loaders/next-app-loader/index.js?name=app%2Fapi%2Fstatus%2F%5Bid%5D%2Froute&page=%2Fapi%2Fstatus%2F%5Bid%5D%2Froute&appPaths=&pagePath=private-next-app-dir%2Fapi%2Fstatus%2F%5Bid%5D%2Froute.ts&appDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels%2Fapp&pageExtensions=tsx&pageExtensions=ts&pageExtensions=jsx&pageExtensions=js&rootDir=%2FUsers%2Fmarcsmith%2FDesktop%2FProjects%2FDog%20Reels&isDev=true&tsconfigPath=tsconfig.json&basePath=&assetPrefix=&nextConfigOutput=&preferredRegion=&middlewareConfig=e30%3D!")));
module.exports = __webpack_exports__;

})();